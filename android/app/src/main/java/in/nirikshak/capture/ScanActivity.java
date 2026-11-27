package in.nirikshak.capture;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.res.ColorStateList;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.os.SystemClock;
import android.provider.Settings;
import android.view.Gravity;
import android.view.Surface;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebView;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

import androidx.activity.ComponentActivity;
import androidx.activity.OnBackPressedCallback;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.camera.core.Camera;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.FocusMeteringAction;
import androidx.camera.core.ImageAnalysis;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.core.ImageProxy;
import androidx.camera.core.Preview;
import androidx.camera.core.UseCaseGroup;
import androidx.camera.core.resolutionselector.ResolutionSelector;
import androidx.camera.core.resolutionselector.ResolutionStrategy;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowCompat;
import androidx.lifecycle.ViewModelProvider;

import android.util.Size;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

public final class ScanActivity extends ComponentActivity {
    private static final int BACKGROUND = Color.rgb(13, 25, 22);
    private static final int SURFACE = Color.rgb(23, 41, 34);
    private static final int TEXT = Color.rgb(243, 247, 235);
    private static final int MUTED = Color.rgb(176, 195, 180);
    private static final int ACCENT = Color.rgb(205, 247, 139);
    private static final int LINE = Color.rgb(53, 77, 64);
    private static final int AMBER = Color.rgb(255, 213, 141);
    private static final int RED = Color.rgb(255, 170, 161);
    private static final ViewGroup.LayoutParams MATCH = new FrameLayout.LayoutParams(-1, -1);

    private enum Screen { HOME, HISTORY, PERMISSION, CAMERA, SUBMISSION, RESULT, REPORT }

    private final ExecutorService frames = Executors.newSingleThreadExecutor();
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private final InspectionApi api = new InspectionApi(BuildConfig.API_BASE);
    private final ActivityResultLauncher<String> cameraPermission = registerForActivityResult(
            new ActivityResultContracts.RequestPermission(), granted -> {
                if (granted) openCamera();
                else showPermission();
            });

    private Screen screen;
    private ScanDraft draft;
    private ProcessCameraProvider provider;
    private Camera camera;
    private PreviewView preview;
    private ImageCapture shutter;
    private boolean takingPhoto;
    private SubmissionModel submission;
    private long cameraGeneration;
    private long resultGeneration;
    private ScanDraft.Panel panel;
    private LinearLayout panelHolder;
    private LinearLayout scanControls;
    private TextView panelDirection;
    private TextView prompt;
    private ProgressBar stability;
    private Button skip;
    private Button retake;
    private Button torch;
    private boolean torchOn;
    private WebView report;
    private JSONObject result;
    private boolean fromHistory;
    private boolean offlineResult;
    private String selectedId;
    private String historyQuery = "";
    private ReportCache cache;
    private TextView networkStatus;
    private long lastFocus;
    private volatile CaptureStep captureStep = new CaptureStep(0, Collections.emptyList(), 0);

    private record CaptureStep(long sequence, List<byte[]> signatures, long startsAt) {}

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        draft = ScanDraft.open(this);
        cache = new ReportCache(this);
        submission = new ViewModelProvider(this).get(SubmissionModel.class);
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override public void handleOnBackPressed() {
                if (screen == Screen.REPORT) showResult(result);
                else if (screen == Screen.RESULT && fromHistory) showHistory();
                else if (screen == Screen.HOME) finish();
                else showHome();
            }
        });
        showHome();
        if (savedInstanceState != null) {
            String previous = savedInstanceState.getString("screen", Screen.HOME.name());
            fromHistory = savedInstanceState.getBoolean("history");
            historyQuery = savedInstanceState.getString("query", "");
            String id = savedInstanceState.getString("inspection");
            if (previous.equals(Screen.HISTORY.name())) showHistory();
            if (draft != null && (previous.equals(Screen.CAMERA.name()) || previous.equals(Screen.SUBMISSION.name()))) continueScan();
            if (id != null && (previous.equals(Screen.RESULT.name()) || previous.equals(Screen.REPORT.name()))) {
                loadInspection(id, previous.equals(Screen.REPORT.name()), null);
            }
        }
        submission.progress().observe(this, this::onSubmissionProgress);
    }

    @Override
    protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        state.putString("screen", screen.name());
        state.putString("inspection", selectedId);
        state.putBoolean("history", fromHistory);
        state.putString("query", historyQuery);
    }

    @Override
    protected void onStart() {
        super.onStart();
        if (screen == Screen.CAMERA && shutter == null && preview != null) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                queueCameraBinding(preview);
            } else {
                showPermission();
            }
        }
    }

    @Override
    protected void onStop() {
        if (screen == Screen.CAMERA) stopCamera();
        super.onStop();
    }

    @Override
    protected void onDestroy() {
        stopCamera();
        destroyReport();
        frames.shutdown();
        network.shutdownNow();
        super.onDestroy();
    }

    private LinearLayout screen(Screen next, boolean scroll) {
        if (screen == Screen.CAMERA) stopCamera();
        destroyReport();
        screen = next;
        resultGeneration++;
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(BACKGROUND);
        ViewCompat.setOnApplyWindowInsetsListener(root, (view, windowInsets) -> {
            Insets insets = windowInsets.getInsets(WindowInsetsCompat.Type.systemBars() | WindowInsetsCompat.Type.displayCutout());
            view.setPadding(insets.left, insets.top, insets.right, insets.bottom);
            return windowInsets;
        });
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(22), dp(10), dp(22), dp(16));
        if (scroll) {
            ScrollView holder = new ScrollView(this);
            holder.setFillViewport(true);
            holder.addView(content, new ScrollView.LayoutParams(-1, -2));
            root.addView(holder, MATCH);
        } else {
            root.addView(content, MATCH);
        }
        setContentView(root);
        ViewCompat.requestApplyInsets(root);
        return content;
    }

    private void showHome() {
        LinearLayout layout = screen(Screen.HOME, true);
        toolbar(layout, "Nirikshak", false);
        space(layout, 16);
        LinearLayout hero = card(layout, 20);
        hero.setBackground(new GradientDrawable(GradientDrawable.Orientation.TL_BR,
                new int[]{0xff294838, 0xff172c24}));
        GradientDrawable heroBackground = (GradientDrawable) hero.getBackground();
        heroBackground.setCornerRadius(dp(24));
        heroBackground.setStroke(dp(1), LINE);
        ImageView logo = new ImageView(this);
        logo.setImageResource(R.drawable.ic_package);
        hero.addView(logo, new LinearLayout.LayoutParams(dp(46), dp(46)));
        space(hero, 18);
        hero.addView(copy("Scan a package", 34, TEXT, true));
        space(hero, 8);
        hero.addView(copy("Turn the package as directed. Photos are taken automatically when each panel is clear and steady.", 16, MUTED, false));
        space(hero, 20);
        boolean active = draft != null && draft.inspectionId().isEmpty();
        if (active) {
            hero.addView(panelStrip(draft.panels(), null));
            space(hero, 12);
        }
        hero.addView(button(active ? "Resume scan" : "New package", true, () -> {
            fromHistory = false;
            offlineResult = false;
            if (!active) {
                try {
                    draft = ScanDraft.create(this);
                } catch (IOException failure) {
                    showMessage(failure.getMessage());
                    return;
                }
            }
            continueScan();
        }));
        space(layout, 18);
        LinearLayout records = card(layout, 16);
        records.addView(copy("Inspections", 21, TEXT, true));
        space(records, 5);
        records.addView(copy("Find saved scans, review declarations, or share a report.", 15, MUTED, false));
        space(records, 12);
        records.addView(button("Browse inspection history", false, this::showHistory));
        if (draft != null && !draft.inspectionId().isEmpty()) {
            space(records, 8);
            records.addView(button("Last inspection", false, this::loadLastInspection));
        }
        SubmissionModel.Progress running = submission.current(draft);
        if (active && (running == null || !running.active())) {
            space(layout, 10);
            layout.addView(button("Discard scan", false, () -> {
                new android.app.AlertDialog.Builder(this)
                        .setMessage("Discard this scan and its photos on this phone?")
                        .setNegativeButton("Keep scan", null)
                        .setPositiveButton("Discard", (dialog, which) -> {
                            draft.discard();
                            draft = null;
                            showHome();
                        }).show();
            }));
        }
    }

    private void continueScan() {
        if (!draft.inspectionId().isEmpty()) {
            loadLastInspection();
        } else if (draft.ready()) {
            SubmissionModel.Progress running = submission.current(draft);
            if (running == null) submit();
            else if (running.result() != null) showResult(running.result());
            else showSubmission(running.failure(), running.message());
        } else if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            openCamera();
        } else {
            cameraPermission.launch(Manifest.permission.CAMERA);
        }
    }

    private void showPermission() {
        LinearLayout layout = screen(Screen.PERMISSION, true);
        toolbar(layout, "Camera access", true);
        space(layout, 30);
        layout.addView(copy("Allow the camera to scan the packet", 32, TEXT, true));
        space(layout, 12);
        layout.addView(copy("Nirikshak needs camera access for automatic package photos.", 17, MUTED, false));
        space(layout, 24);
        if (shouldShowRequestPermissionRationale(Manifest.permission.CAMERA)) {
            layout.addView(button("Allow camera", true, () -> cameraPermission.launch(Manifest.permission.CAMERA)));
        } else {
            layout.addView(button("Open app settings", true, () -> startActivity(new Intent(
                    Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", getPackageName(), null)))));
        }
        space(layout, 8);
        layout.addView(button("Continue after allowing", false, this::continueScan));
    }

    private void openCamera() {
        if (draft.ready()) {
            submit();
            return;
        }
        LinearLayout layout = screen(Screen.CAMERA, false);
        LinearLayout cameraBar = toolbar(layout, "Package scan", true);
        torch = button("Light", false, this::toggleTorch);
        torch.setVisibility(View.GONE);
        torch.setContentDescription("Turn flashlight on");
        cameraBar.addView(torch, new LinearLayout.LayoutParams(dp(74), dp(48)));
        space(layout, 7);
        panelHolder = new LinearLayout(this);
        layout.addView(panelHolder, new LinearLayout.LayoutParams(-1, -2));
        space(layout, 12);
        FrameLayout area = new FrameLayout(this);
        area.setBackground(surface(Color.BLACK, 18, LINE));
        area.setClipToOutline(true);
        preview = new PreviewView(this);
        preview.setImplementationMode(PreviewView.ImplementationMode.COMPATIBLE);
        preview.setScaleType(PreviewView.ScaleType.FILL_CENTER);
        area.addView(preview, MATCH);
        area.addView(new GuideOverlay(), MATCH);
        scanControls = new LinearLayout(this);
        scanControls.setOrientation(LinearLayout.VERTICAL);
        scanControls.setPadding(dp(14), dp(10), dp(14), dp(12));
        scanControls.setBackground(surface(SURFACE, 18, LINE));
        if (getResources().getConfiguration().screenWidthDp > getResources().getConfiguration().screenHeightDp) {
            LinearLayout row = new LinearLayout(this);
            row.addView(area, new LinearLayout.LayoutParams(0, -1, 1.5f));
            LinearLayout.LayoutParams help = new LinearLayout.LayoutParams(0, -1, 1);
            help.setMarginStart(dp(12));
            scanControls.setGravity(Gravity.CENTER_VERTICAL);
            ScrollView guidance = new ScrollView(this);
            guidance.setFillViewport(true);
            guidance.addView(scanControls, new ScrollView.LayoutParams(-1, -2));
            row.addView(guidance, help);
            layout.addView(row, new LinearLayout.LayoutParams(-1, 0, 1));
        } else {
            layout.addView(area, new LinearLayout.LayoutParams(-1, 0, 1));
            space(layout, 12);
            layout.addView(scanControls);
        }

        panelDirection = copy("", 14, MUTED, false);
        scanControls.addView(panelDirection);
        space(scanControls, 4);
        prompt = copy("Starting camera…", 22, TEXT, true);
        prompt.setMinimumHeight(dp(51));
        prompt.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        scanControls.addView(prompt);
        stability = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        stability.setMax(FrameGuide.REQUIRED_STABLE_FRAMES);
        stability.setProgressTintList(ColorStateList.valueOf(ACCENT));
        stability.setProgressBackgroundTintList(ColorStateList.valueOf(LINE));
        stability.setContentDescription("Automatic capture progress");
        scanControls.addView(stability, new LinearLayout.LayoutParams(-1, dp(5)));
        skip = button("Skip side and analyze", false, this::completeCapture);
        LinearLayout.LayoutParams skipParams = new LinearLayout.LayoutParams(-1, -2);
        skipParams.topMargin = dp(7);
        scanControls.addView(skip, skipParams);
        retake = button("Retake last panel", false, this::retakeLastPanel);
        LinearLayout.LayoutParams retakeParams = new LinearLayout.LayoutParams(-1, -2);
        retakeParams.topMargin = dp(7);
        scanControls.addView(retake, retakeParams);
        showPanel(true);
        queueCameraBinding(preview);
    }

    private void showPanel(boolean initial) {
        List<ScanDraft.Panel> done = draft.panels();
        panel = done.contains(ScanDraft.Panel.FRONT)
                ? (done.contains(ScanDraft.Panel.REAR) ? ScanDraft.Panel.SIDE : ScanDraft.Panel.REAR)
                : ScanDraft.Panel.FRONT;
        panelHolder.removeAllViews();
        panelHolder.addView(panelStrip(done, panel), new LinearLayout.LayoutParams(-1, -2));
        panelDirection.setText(panel.direction);
        skip.setVisibility(panel == ScanDraft.Panel.SIDE ? View.VISIBLE : View.GONE);
        skip.setEnabled(true);
        retake.setVisibility(done.isEmpty() ? View.GONE : View.VISIBLE);
        retake.setEnabled(true);
        stability.setProgress(0);
        takingPhoto = false;
        captureStep = new CaptureStep(captureStep.sequence() + 1, draft.signatures(),
                SystemClock.elapsedRealtime() + (initial ? 0 : 400));
        if (initial) prompt.setText("Starting camera…");
        else prompt.setText(panel == ScanDraft.Panel.REAR ? "Turn to the back" : "Move to the side");
    }

    private void retakeLastPanel() {
        List<ScanDraft.Panel> captured = draft.panels();
        if (takingPhoto || captured.isEmpty()) return;
        ScanDraft.Panel last = captured.get(captured.size() - 1);
        try {
            draft.remove(last);
            showPanel(true);
            prompt.setText("Show the " + last.title.toLowerCase(Locale.ROOT) + " again");
        } catch (IOException failure) {
            showMessage("Could not replace that photo.");
        }
    }

    private void queueCameraBinding(PreviewView target) {
        long generation = ++cameraGeneration;
        target.post(() -> {
            if (screen != Screen.CAMERA || preview != target || generation != cameraGeneration || isDestroyed()) return;
            var future = ProcessCameraProvider.getInstance(this);
            future.addListener(() -> {
                if (generation != cameraGeneration || isDestroyed()) return;
                try {
                    provider = future.get();
                    bindCamera(target, generation);
                } catch (Exception failure) {
                    prompt.setText("Camera unavailable. Go back and try again.");
                }
            }, ContextCompat.getMainExecutor(this));
        });
    }

    private void bindCamera(PreviewView target, long generation) {
        int rotation = target.getDisplay() == null ? Surface.ROTATION_0 : target.getDisplay().getRotation();
        Preview live = new Preview.Builder().setTargetRotation(rotation).build();
        live.setSurfaceProvider(target.getSurfaceProvider());
        shutter = new ImageCapture.Builder().setTargetRotation(rotation).setJpegQuality(92)
                .setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
                .setResolutionSelector(resolution(2000, 1500)).build();
        ImageAnalysis analysis = new ImageAnalysis.Builder().setTargetRotation(rotation)
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setResolutionSelector(resolution(640, 480)).build();
        analysis.setAnalyzer(frames, new ImageAnalysis.Analyzer() {
            private long last;
            private long sequence = -1;
            private FrameGuide guide;

            @Override public void analyze(ImageProxy image) {
                byte[] samples;
                FrameGuide.Reading reading;
                CaptureStep active = captureStep;
                try {
                    long now = SystemClock.elapsedRealtime();
                    if (now - last < 150 || now < active.startsAt()) return;
                    last = now;
                    if (sequence != active.sequence()) {
                        sequence = active.sequence();
                        guide = new FrameGuide(active.signatures());
                    }
                    samples = uprightLuma(image);
                    reading = guide.measure(samples);
                } finally {
                    image.close();
                }
                runOnUiThread(() -> showGuide(generation, active.sequence(), reading, samples));
            }
        });
        UseCaseGroup.Builder useCases = new UseCaseGroup.Builder()
                .addUseCase(live).addUseCase(shutter).addUseCase(analysis);
        if (target.getViewPort() != null) useCases.setViewPort(target.getViewPort());
        provider.unbindAll();
        camera = provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, useCases.build());
        torchOn = false;
        torch.setEnabled(true);
        torch.setText("Light");
        torch.setContentDescription("Turn flashlight on");
        torch.setVisibility(camera.getCameraInfo().hasFlashUnit() ? View.VISIBLE : View.GONE);
    }

    private void toggleTorch() {
        if (camera == null || !camera.getCameraInfo().hasFlashUnit()) return;
        Camera active = camera;
        boolean enable = !torchOn;
        var change = active.getCameraControl().enableTorch(enable);
        torch.setEnabled(false);
        change.addListener(() -> {
            if (camera != active) return;
            torch.setEnabled(true);
            try {
                change.get();
                torchOn = enable;
                torch.setText(enable ? "Light on" : "Light");
                torch.setContentDescription(enable ? "Turn flashlight off" : "Turn flashlight on");
            } catch (Exception failure) {
                showMessage("The flashlight is unavailable.");
            }
        }, ContextCompat.getMainExecutor(this));
    }

    private static ResolutionSelector resolution(int width, int height) {
        return new ResolutionSelector.Builder().setResolutionStrategy(new ResolutionStrategy(
                new Size(width, height), ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER)).build();
    }

    static byte[] uprightLuma(ImageProxy image) {
        var plane = image.getPlanes()[0];
        ByteBuffer data = plane.getBuffer();
        int rowStride = plane.getRowStride(), pixelStride = plane.getPixelStride();
        int offset = data.position();
        Rect crop = image.getCropRect();
        int rotation = image.getImageInfo().getRotationDegrees();
        int width = crop.width(), height = crop.height();
        byte[] pixels = new byte[FrameGuide.WIDTH * FrameGuide.HEIGHT];
        for (int y = 0; y < FrameGuide.HEIGHT; y++) {
            float v = (y + .5f) / FrameGuide.HEIGHT;
            for (int x = 0; x < FrameGuide.WIDTH; x++) {
                float u = (x + .5f) / FrameGuide.WIDTH;
                int sx = (int) (width * switch (rotation) {
                    case 90 -> v;
                    case 180 -> 1 - u;
                    case 270 -> 1 - v;
                    default -> u;
                });
                int sy = (int) (height * switch (rotation) {
                    case 90 -> 1 - u;
                    case 180 -> 1 - v;
                    case 270 -> u;
                    default -> v;
                });
                int lx = Math.max(0, sx - 2), rx = Math.min(width - 1, sx + 2);
                int ty = Math.max(0, sy - 2), by = Math.min(height - 1, sy + 2);
                int upper = offset + (crop.top + ty) * rowStride + crop.left * pixelStride;
                int lower = offset + (crop.top + by) * rowStride + crop.left * pixelStride;
                pixels[y * FrameGuide.WIDTH + x] = (byte) ((Byte.toUnsignedInt(data.get(upper + lx * pixelStride))
                        + Byte.toUnsignedInt(data.get(upper + rx * pixelStride))
                        + Byte.toUnsignedInt(data.get(lower + lx * pixelStride))
                        + Byte.toUnsignedInt(data.get(lower + rx * pixelStride))) / 4);
            }
        }
        return pixels;
    }

    private void showGuide(long generation, long sequence, FrameGuide.Reading reading, byte[] samples) {
        if (generation != cameraGeneration || sequence != captureStep.sequence()
                || screen != Screen.CAMERA || takingPhoto || shutter == null) return;
        String message = reading.prompt().message;
        if (!message.contentEquals(prompt.getText())) prompt.setText(message);
        stability.setProgress(reading.stableFrames());
        if (reading.prompt() == FrameGuide.Prompt.FOCUS && camera != null
                && SystemClock.elapsedRealtime() - lastFocus > 2800) {
            lastFocus = SystemClock.elapsedRealtime();
            var center = preview.getMeteringPointFactory().createPoint(preview.getWidth() / 2f, preview.getHeight() / 2f);
            camera.getCameraControl().startFocusAndMetering(
                    new FocusMeteringAction.Builder(center).setAutoCancelDuration(2, TimeUnit.SECONDS).build());
        }
        if (reading.ready()) takePhoto(generation, samples);
    }

    private void takePhoto(long generation, byte[] samples) {
        ScanDraft active = draft;
        ScanDraft.Panel captured = panel;
        File temporary;
        try {
            temporary = active.temporaryImage(captured);
        } catch (IOException failure) {
            stopCamera();
            prompt.setText("Photo storage is unavailable. Free some space and reopen the scan.");
            return;
        }
        takingPhoto = true;
        prompt.setText("Capturing " + captured.title.toLowerCase(java.util.Locale.ROOT) + "…");
        skip.setEnabled(false);
        retake.setEnabled(false);
        shutter.takePicture(new ImageCapture.OutputFileOptions.Builder(temporary).build(),
                ContextCompat.getMainExecutor(this), new ImageCapture.OnImageSavedCallback() {
                    @Override public void onImageSaved(ImageCapture.OutputFileResults saved) {
                        if (generation != cameraGeneration || isDestroyed()) {
                            temporary.delete();
                            return;
                        }
                        try {
                            active.keep(captured, temporary, samples);
                            performHapticFeedback();
                            if (captured == ScanDraft.Panel.SIDE) completeCapture();
                            else showPanel(false);
                        } catch (IOException failure) {
                            onError(new ImageCaptureException(ImageCapture.ERROR_FILE_IO, failure.getMessage(), failure));
                        }
                    }

                    @Override public void onError(ImageCaptureException error) {
                        temporary.delete();
                        if (generation != cameraGeneration || isDestroyed()) return;
                        takingPhoto = false;
                        skip.setEnabled(true);
                        retake.setEnabled(true);
                        stability.setProgress(0);
                        if (error.getImageCaptureError() == ImageCapture.ERROR_FILE_IO) {
                            stopCamera();
                            prompt.setText("Could not save the photo. Check available storage, then resume.");
                        } else {
                            captureStep = new CaptureStep(captureStep.sequence() + 1, draft.signatures(),
                                    SystemClock.elapsedRealtime() + 1200);
                            prompt.setText("Capture interrupted. Hold steady to try again.");
                        }
                    }
                });
    }

    private void completeCapture() {
        if (!draft.finishCapture() && !draft.ready()) {
            stopCamera();
            prompt.setText("The scan could not be saved. Go back and resume when storage is available.");
            return;
        }
        submit();
    }

    private void stopCamera() {
        cameraGeneration++;
        takingPhoto = false;
        camera = null;
        shutter = null;
        if (provider != null) provider.unbindAll();
    }

    private void performHapticFeedback() {
        int gesture = android.os.Build.VERSION.SDK_INT >= 30
                ? android.view.HapticFeedbackConstants.CONFIRM : android.view.HapticFeedbackConstants.LONG_PRESS;
        getWindow().getDecorView().performHapticFeedback(gesture);
    }

    private void submit() {
        fromHistory = false;
        offlineResult = false;
        showSubmission(null, "Preparing captured photos…");
        submission.submit(draft);
    }

    private void onSubmissionProgress(SubmissionModel.Progress progress) {
        if (draft == null || !draft.requestId.equals(progress.requestId())) return;
        if (screen == Screen.SUBMISSION) {
            if (progress.result() != null) {
                JSONObject saved = progress.result();
                network.execute(() -> cache.write(saved.optString("id") + ".json", saved.toString()));
                showResult(saved);
            }
            else if (progress.failure() != null) showSubmission(progress.failure(), "");
            else networkStatus.setText(progress.message());
        } else if (screen == Screen.HOME && !progress.active()) {
            showHome();
        }
    }

    private void showSubmission(Exception failure, String message) {
        LinearLayout layout = screen(Screen.SUBMISSION, true);
        toolbar(layout, "Package analysis", true);
        space(layout, 43);
        layout.addView(copy(failure == null ? "Reading your package" : "Analysis paused", 36, TEXT, true));
        space(layout, 15);
        networkStatus = copy(failure == null ? message : errorMessage(failure), 17, MUTED, false);
        networkStatus.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        layout.addView(networkStatus);
        space(layout, 16);
        if (failure == null) {
            ProgressBar progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
            progress.setIndeterminate(true);
            progress.setIndeterminateTintList(ColorStateList.valueOf(ACCENT));
            progress.setContentDescription("Analysis in progress");
            layout.addView(progress, new LinearLayout.LayoutParams(-1, dp(5)));
        } else {
            layout.addView(copy("Your photos are saved on this phone.", 15, MUTED, false));
            space(layout, 16);
            layout.addView(button("Retry analysis", true, this::submit));
        }
    }

    private void loadLastInspection() {
        fromHistory = false;
        loadInspection(draft.inspectionId(), false, null);
    }

    private void showHistory() {
        LinearLayout layout = screen(Screen.HISTORY, true);
        LinearLayout bar = toolbar(layout, "Inspections", true);
        bar.addView(button("Refresh", false, this::showHistory), new LinearLayout.LayoutParams(dp(84), dp(48)));
        space(layout, 14);
        EditText search = new EditText(this);
        search.setSingleLine(true);
        search.setInputType(android.text.InputType.TYPE_CLASS_TEXT | android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
        search.setHint("Search package or inspection ID");
        search.setContentDescription("Search saved inspections");
        search.setText(historyQuery);
        search.setTextSize(16);
        search.setTextColor(TEXT);
        search.setHintTextColor(MUTED);
        search.setPadding(dp(14), dp(10), dp(14), dp(10));
        search.setMinimumHeight(dp(48));
        search.setBackground(surface(SURFACE, 12, LINE));
        layout.setFocusableInTouchMode(true);
        layout.requestFocus();
        layout.addView(search);
        space(layout, 12);
        TextView state = copy("Loading inspections…", 14, MUTED, false);
        layout.addView(state);
        LinearLayout rows = new LinearLayout(this);
        rows.setOrientation(LinearLayout.VERTICAL);
        layout.addView(rows);
        long generation = resultGeneration;
        network.execute(() -> {
            JSONArray records;
            boolean offline = false;
            try {
                records = summarizeHistory(api.inspections());
                cache.write("history.json", records.toString());
            } catch (Exception failure) {
                try {
                    String stored = cache.read("history.json");
                    if (stored == null) throw failure;
                    records = new JSONArray(stored);
                    offline = true;
                } catch (Exception ignored) {
                    runOnUiThread(() -> {
                        if (isDestroyed() || resultGeneration != generation) return;
                        state.setText(errorMessage(failure));
                    });
                    return;
                }
            }
            JSONArray available = records;
            boolean cached = offline;
            runOnUiThread(() -> {
                if (isDestroyed() || resultGeneration != generation) return;
                state.setText(cached ? "Offline · showing the last loaded list" : available.length() + " saved inspections");
                renderHistory(rows, available);
                search.addTextChangedListener(new android.text.TextWatcher() {
                    @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
                    @Override public void onTextChanged(CharSequence s, int start, int before, int count) {
                        historyQuery = s.toString();
                        renderHistory(rows, available);
                    }
                    @Override public void afterTextChanged(android.text.Editable text) {}
                });
                historyQuery = search.getText().toString();
                renderHistory(rows, available);
            });
        });
    }

    private JSONArray summarizeHistory(JSONArray records) throws org.json.JSONException {
        JSONArray rows = new JSONArray();
        for (int i = 0; i < records.length(); i++) {
            JSONObject record = records.getJSONObject(i);
            JSONObject row = new JSONObject();
            for (String key : new String[]{"id", "product_name", "brand", "timestamp", "final_outcome"}) {
                row.put(key, record.optString(key));
            }
            row.put("analyzed", record.optJSONObject("analysis") != null);
            rows.put(row);
        }
        return rows;
    }

    private void renderHistory(LinearLayout rows, JSONArray records) {
        rows.removeAllViews();
        String filter = historyQuery.trim().toLowerCase(Locale.ROOT);
        for (int i = 0; i < records.length(); i++) {
            JSONObject row = records.optJSONObject(i);
            String id = row.optString("id");
            String name = displayName(row);
            if (!(name + " " + row.optString("brand") + " " + id).toLowerCase(Locale.ROOT).contains(filter)) continue;
            space(rows, 9);
            LinearLayout item = card(rows, 15);
            item.setBackground(new android.graphics.drawable.RippleDrawable(ColorStateList.valueOf(0x33cdf78b),
                    surface(SURFACE, 16, LINE), null));
            String status = row.optBoolean("analyzed") ? outcomeLabel(row) : "Awaiting analysis";
            item.addView(copy(name, 18, TEXT, true));
            space(item, 4);
            item.addView(copy(status, 14, outcomeColor(status), true));
            String timestamp = row.optString("timestamp");
            item.addView(copy(timestamp.substring(0, Math.min(10, timestamp.length())), 13, MUTED, false));
            item.setContentDescription(name + ", " + status);
            item.setFocusable(true);
            item.setOnClickListener(view -> {
                fromHistory = true;
                loadInspection(id, false, row);
            });
            ViewCompat.setAccessibilityDelegate(item, new androidx.core.view.AccessibilityDelegateCompat() {
                @Override public void onInitializeAccessibilityNodeInfo(View host,
                        androidx.core.view.accessibility.AccessibilityNodeInfoCompat info) {
                    super.onInitializeAccessibilityNodeInfo(host, info);
                    info.setClassName(Button.class.getName());
                }
            });
        }
        if (rows.getChildCount() == 0) {
            space(rows, 20);
            rows.addView(copy(filter.isEmpty() ? "No saved inspections yet." : "No inspections match that search.", 16, MUTED, false));
        }
    }

    private void loadInspection(String id, boolean openReport, JSONObject summary) {
        selectedId = id;
        LinearLayout layout = screen(Screen.RESULT, true);
        toolbar(layout, "Inspection", true);
        space(layout, 20);
        TextView state = copy("Loading saved inspection…", 19, TEXT, true);
        layout.addView(state);
        long generation = resultGeneration;
        network.execute(() -> {
            try {
                JSONObject saved = api.inspection(id);
                cache.write(id + ".json", saved.toString());
                runOnUiThread(() -> {
                    if (isDestroyed() || resultGeneration != generation) return;
                    offlineResult = false;
                    showResult(saved);
                    if (openReport) showReport(id);
                });
            } catch (Exception failure) {
                JSONObject saved = summary;
                boolean serverRejected = failure instanceof InspectionApi.ApiError error && error.code == 404;
                if (!serverRejected) {
                    try {
                        String stored = cache.read(id + ".json");
                        if (stored != null) saved = new JSONObject(stored);
                    } catch (org.json.JSONException ignored) {
                        // A saved summary can still open a cached report.
                    }
                }
                JSONObject local = serverRejected ? null : saved;
                runOnUiThread(() -> {
                    if (isDestroyed() || resultGeneration != generation) return;
                    if (local != null) {
                        offlineResult = true;
                        showResult(local);
                        if (openReport) showReport(id);
                        return;
                    }
                    state.setText(errorMessage(failure));
                    space(layout, 12);
                    layout.addView(button("Retry", true, () -> loadInspection(id, openReport, summary)));
                });
            }
        });
    }

    private void showResult(JSONObject saved) {
        if (saved == null) {
            showHome();
            return;
        }
        result = saved;
        selectedId = saved.optString("id");
        LinearLayout layout = screen(Screen.RESULT, true);
        toolbar(layout, "Inspection", true);
        space(layout, 14);
        LinearLayout header = card(layout, 17);
        header.addView(copy(displayName(saved), 29, TEXT, true));
        space(header, 7);
        TextView identity = copy(selectedId, 12, MUTED, false);
        identity.setTextIsSelectable(true);
        header.addView(identity);
        space(header, 10);
        JSONObject analysis = saved.optJSONObject("analysis");
        boolean analyzed = analysis != null || saved.optBoolean("analyzed");
        String outcome = analyzed ? outcomeLabel(saved) : "Awaiting analysis";
        header.addView(copy(outcome, 17, outcomeColor(outcome), true));
        if (offlineResult) {
            space(header, 6);
            header.addView(copy("Offline · last saved copy", 14, AMBER, false));
        }
        JSONObject classification = analysis == null ? null : analysis.optJSONObject("classification");
        if (classification != null) {
            space(header, 6);
            header.addView(copy(classification.optString("reason"), 14, MUTED, false));
        }
        if (!analyzed) return;
        space(layout, 12);
        layout.addView(button("View full report", true, () -> showReport(selectedId)));
        space(layout, 7);
        addShareButton(layout, selectedId);
        renderChecks(layout, analysis);
        JSONArray fields = analysis == null ? null : analysis.optJSONArray("fields");
        if (fields == null || fields.length() == 0) return;
        space(layout, 20);
        layout.addView(copy("Label readings", 21, TEXT, true));
        space(layout, 5);
        layout.addView(copy("Compare these OCR readings with the printed label.", 14, MUTED, false));
        space(layout, 9);
        LinearLayout readings = card(layout, 14);
        for (int i = 0; fields != null && i < fields.length(); i++) {
            JSONObject entry = fields.optJSONObject(i);
            if (entry == null) continue;
            String label = switch (entry.optString("field")) {
                case "generic_name" -> "Product type";
                case "net_quantity" -> "Net quantity";
                case "mrp" -> "Retail price";
                case "date" -> "Packed or manufactured";
                case "expiry" -> "Best before / use by";
                case "manufacturer" -> "Manufacturer / packer";
                case "consumer_care" -> "Consumer care";
                case "country_of_origin" -> "Country of origin";
                default -> entry.optString("field").replace('_', ' ');
            };
            if (i > 0) {
                space(readings, 9);
                View divider = new View(this);
                divider.setBackgroundColor(LINE);
                readings.addView(divider, new LinearLayout.LayoutParams(-1, dp(1)));
                space(readings, 9);
            }
            readings.addView(copy(label, 13, MUTED, false));
            boolean observed = "observed".equals(entry.optString("status")) && !entry.isNull("value");
            String reading = observed ? entry.optString("value")
                    : "conflict".equals(entry.optString("status")) ? "Conflicting readings" : "Unread";
            readings.addView(copy(reading, 17, observed ? TEXT : MUTED, observed));
        }
    }

    private void renderChecks(LinearLayout layout, JSONObject analysis) {
        JSONObject checks = analysis == null ? null : analysis.optJSONObject("checks");
        JSONArray entries = checks == null ? null : checks.optJSONArray("results");
        if (entries == null || entries.length() == 0) return;
        int passed = 0;
        int flagged = 0;
        int review = 0;
        for (int i = 0; i < entries.length(); i++) {
            JSONObject check = entries.optJSONObject(i);
            if (check == null) continue;
            switch (check.optString("status")) {
                case "pass" -> passed++;
                case "fail" -> flagged++;
                case "insufficient_evidence" -> review++;
            }
        }
        space(layout, 15);
        LinearLayout section = card(layout, 14);
        section.addView(copy("Declaration checks", 19, TEXT, true));
        space(section, 8);
        LinearLayout numbers = new LinearLayout(this);
        section.addView(numbers);
        checkCount(numbers, passed, "Passed", ACCENT);
        checkCount(numbers, flagged, "Flagged", RED);
        checkCount(numbers, review, "Need evidence", AMBER);
    }

    private void checkCount(LinearLayout row, int count, String label, int color) {
        LinearLayout cell = new LinearLayout(this);
        cell.setOrientation(LinearLayout.VERTICAL);
        cell.addView(copy(String.valueOf(count), 23, color, true));
        cell.addView(copy(label, 13, MUTED, false));
        row.addView(cell, new LinearLayout.LayoutParams(0, -2, 1));
    }

    private static String displayName(JSONObject saved) {
        String name = saved.optString("product_name");
        return name.trim().isEmpty() || name.equals("Generic Commodity Sample") ? "Package inspection" : name;
    }

    private static String outcomeLabel(JSONObject saved) {
        return switch (saved.optString("final_outcome")) {
            case "Potential Non-Compliance" -> "Potential non-compliance";
            case "Compliant within Implemented Checks" -> "Implemented checks passed";
            default -> "Manual review required";
        };
    }

    private static int outcomeColor(String outcome) {
        return switch (outcome) {
            case "Potential non-compliance" -> RED;
            case "Implemented checks passed" -> ACCENT;
            case "Manual review required" -> AMBER;
            default -> MUTED;
        };
    }

    private void showReport(String id) {
        LinearLayout layout = screen(Screen.REPORT, false);
        toolbar(layout, "Inspection report", true);
        addShareButton(layout, id);
        space(layout, 10);
        TextView state = copy("Loading report…", 16, MUTED, false);
        layout.addView(state);
        long generation = resultGeneration;
        network.execute(() -> {
            String key = id + ".html";
            String html;
            boolean offline = false;
            try {
                html = api.report(id);
                cache.write(key, html);
            } catch (Exception failure) {
                boolean invalidated = failure instanceof InspectionApi.ApiError error && (error.code == 404 || error.code == 409);
                if (invalidated) cache.remove(key);
                html = invalidated ? null : cache.read(key);
                if (html == null) {
                    runOnUiThread(() -> {
                        if (isDestroyed() || resultGeneration != generation) return;
                        state.setText(errorMessage(failure));
                        space(layout, 8);
                        layout.addView(button("Retry report", true, () -> showReport(id)));
                    });
                    return;
                }
                offline = true;
            }
            String document = html;
            boolean cached = offline;
            runOnUiThread(() -> {
                if (isDestroyed() || resultGeneration != generation) return;
                if (cached) {
                    state.setText("Offline · last opened copy");
                    state.setTextColor(AMBER);
                    state.setPadding(0, 0, 0, dp(8));
                } else {
                    layout.removeView(state);
                }
                displayReport(layout, document);
            });
        });
    }

    private void displayReport(LinearLayout layout, String html) {
        report = new WebView(this);
        report.getSettings().setAllowFileAccess(false);
        report.getSettings().setAllowContentAccess(false);
        report.getSettings().setBlockNetworkLoads(true);
        report.getSettings().setBuiltInZoomControls(true);
        report.getSettings().setDisplayZoomControls(false);
        report.setBackgroundColor(Color.WHITE);
        report.setOutlineProvider(new android.view.ViewOutlineProvider() {
            @Override public void getOutline(View view, android.graphics.Outline outline) {
                outline.setRoundRect(0, 0, view.getWidth(), view.getHeight(), dp(14));
            }
        });
        report.setClipToOutline(true);
        layout.addView(report, new LinearLayout.LayoutParams(-1, 0, 1));
        String csp = "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; img-src data:; style-src 'unsafe-inline'\">";
        String mobileCss = "<style>@media(max-width:640px){body{margin:0;padding:15px}"
                + ".evidence,.outcome,.signoff{grid-template-columns:1fr}.photos{grid-template-columns:repeat(auto-fit,minmax(90px,1fr))}"
                + ".photos img,.photos.n2 img,.photos.n3 img{max-height:150px}td.cite,th{white-space:normal}"
                + ".integrity td:nth-child(n){width:auto}pre{overflow-wrap:anywhere}.masthead{flex-wrap:wrap}}</style>";
        report.loadDataWithBaseURL(null, html.replace("<head>", "<head>" + csp)
                .replace("</head>", mobileCss + "</head>"), "text/html", "UTF-8", null);
    }

    private void addShareButton(LinearLayout layout, String id) {
        Button share = button("Share PDF", false, () -> {});
        share.setOnClickListener(view -> {
            share.setEnabled(false);
            share.setText("Preparing PDF…");
            long generation = resultGeneration;
            network.execute(() -> {
                try {
                    byte[] data = api.pdf(id);
                    if (data.length < 5 || !new String(data, 0, 5, java.nio.charset.StandardCharsets.US_ASCII).equals("%PDF-")) {
                        throw new IOException("The server did not return a PDF.");
                    }
                    File exports = new File(getCacheDir(), "report-exports");
                    if (!exports.isDirectory() && !exports.mkdirs()) throw new IOException("Could not prepare the PDF for sharing.");
                    File[] older = exports.listFiles();
                    if (older != null) {
                        long expiry = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(1);
                        for (File item : older) {
                            if (item.lastModified() < expiry) item.delete();
                        }
                    }
                    File file = File.createTempFile(id + "-", ".pdf", exports);
                    Files.write(file.toPath(), data);
                    Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".reports", file, id + ".pdf");
                    runOnUiThread(() -> {
                        if (isDestroyed() || resultGeneration != generation) return;
                        share.setEnabled(true);
                        share.setText("Share PDF");
                        Intent send = new Intent(Intent.ACTION_SEND).setType("application/pdf")
                                .putExtra(Intent.EXTRA_STREAM, uri)
                                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        startActivity(Intent.createChooser(send, "Share inspection report"));
                    });
                } catch (Exception failure) {
                    runOnUiThread(() -> {
                        if (isDestroyed() || resultGeneration != generation) return;
                        share.setEnabled(true);
                        share.setText("Share PDF");
                        showMessage(errorMessage(failure));
                    });
                }
            });
        });
        layout.addView(share);
    }

    private void destroyReport() {
        if (report == null) return;
        if (report.getParent() instanceof ViewGroup parent) parent.removeView(report);
        report.destroy();
        report = null;
    }

    private static String errorMessage(Exception failure) {
        if (failure instanceof java.net.SocketTimeoutException
                || failure instanceof java.net.ConnectException || failure instanceof java.net.UnknownHostException) {
            return BuildConfig.API_BASE.startsWith("http://127.0.0.1")
                    ? "Server unreachable. Reconnect USB and restore port forwarding, then retry."
                    : "Server unreachable. Check your network connection and retry.";
        }
        if (failure instanceof org.json.JSONException) return "The inspection server returned an unreadable response.";
        return failure.getMessage() == null ? "The server request failed. Retry in a moment." : failure.getMessage();
    }

    private void showMessage(String message) {
        android.widget.Toast.makeText(this, message, android.widget.Toast.LENGTH_LONG).show();
    }

    private LinearLayout toolbar(LinearLayout layout, String title, boolean back) {
        LinearLayout row = new LinearLayout(this);
        row.setGravity(Gravity.CENTER_VERTICAL);
        if (back) {
            Button previous = button("←", false, () -> getOnBackPressedDispatcher().onBackPressed());
            previous.setTextSize(19);
            previous.setContentDescription("Back");
            row.addView(previous, new LinearLayout.LayoutParams(dp(48), dp(48)));
            View spacer = new View(this);
            row.addView(spacer, new LinearLayout.LayoutParams(dp(12), 1));
        }
        TextView heading = copy(title, 19, TEXT, true);
        ViewCompat.setAccessibilityHeading(heading, true);
        row.addView(heading, new LinearLayout.LayoutParams(0, -2, 1));
        row.setMinimumHeight(dp(48));
        layout.addView(row);
        return row;
    }

    private LinearLayout card(LinearLayout parent, int padding) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(padding), dp(padding), dp(padding), dp(padding));
        card.setBackground(surface(SURFACE, 18, LINE));
        parent.addView(card, new LinearLayout.LayoutParams(-1, -2));
        return card;
    }

    private LinearLayout panelStrip(List<ScanDraft.Panel> done, ScanDraft.Panel current) {
        LinearLayout row = new LinearLayout(this);
        for (ScanDraft.Panel item : ScanDraft.Panel.values()) {
            boolean completed = done.contains(item);
            TextView state = copy((completed ? "✓  " : "") + item.title, 14,
                    item == current ? BACKGROUND : completed ? ACCENT : MUTED, true);
            state.setGravity(Gravity.CENTER);
            state.setBackground(surface(item == current ? ACCENT : SURFACE, 12, LINE));
            state.setContentDescription(item.title + (completed ? " captured" : item == current ? " current panel" : ""));
            LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0, dp(39), 1);
            if (item != ScanDraft.Panel.FRONT) params.setMargins(dp(7), 0, 0, 0);
            row.addView(state, params);
        }
        return row;
    }

    private Button button(String label, boolean primary, Runnable action) {
        Button view = new Button(this);
        view.setText(label);
        view.setAllCaps(false);
        view.setTextSize(15);
        view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        view.setMinHeight(dp(48));
        view.setMinimumWidth(dp(48));
        view.setTextColor(primary ? BACKGROUND : TEXT);
        view.setBackground(new android.graphics.drawable.RippleDrawable(
                ColorStateList.valueOf(primary ? 0x22000000 : 0x33cdf78b),
                surface(primary ? ACCENT : SURFACE, 14, primary ? ACCENT : LINE), null));
        view.setOnClickListener(ignored -> action.run());
        return view;
    }

    private TextView copy(String text, int size, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setGravity(Gravity.CENTER_VERTICAL);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }

    private GradientDrawable surface(int fill, int radius, int stroke) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fill);
        drawable.setCornerRadius(dp(radius));
        drawable.setStroke(dp(1), stroke);
        return drawable;
    }

    private void space(LinearLayout layout, int height) {
        layout.addView(new View(this), new LinearLayout.LayoutParams(1, dp(height)));
    }

    private int dp(int pixels) {
        return Math.round(pixels * getResources().getDisplayMetrics().density);
    }

    private final class GuideOverlay extends View {
        private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);

        GuideOverlay() {
            super(ScanActivity.this);
            setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
        }

        @Override protected void onDraw(Canvas canvas) {
            float left = getWidth() / 8f;
            float right = getWidth() - left;
            float top = getHeight() / 8f;
            float bottom = getHeight() - top;
            paint.setColor(0x48000000);
            paint.setStyle(Paint.Style.FILL);
            canvas.drawRect(0, 0, getWidth(), top, paint);
            canvas.drawRect(0, bottom, getWidth(), getHeight(), paint);
            canvas.drawRect(0, top, left, bottom, paint);
            canvas.drawRect(right, top, getWidth(), bottom, paint);
            paint.setColor(ACCENT);
            paint.setStrokeWidth(dp(3));
            paint.setStrokeCap(Paint.Cap.ROUND);
            float corner = dp(18);
            for (int i = 0; i < 2; i++) {
                float x = i == 0 ? left : right;
                for (int j = 0; j < 2; j++) {
                    float y = j == 0 ? top : bottom;
                    canvas.drawLine(x, y, x + (x == left ? corner : -corner), y, paint);
                    canvas.drawLine(x, y, x, y + (y == top ? corner : -corner), paint);
                }
            }
        }
    }
}
