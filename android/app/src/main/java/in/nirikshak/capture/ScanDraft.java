package in.nirikshak.capture;

import android.content.Context;
import android.content.SharedPreferences;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

final class ScanDraft {
    enum Panel {
        FRONT("front", "Front", "Fill the guide with the front of the packet."),
        REAR("rear", "Back", "Turn to the panel with the price, weight or ingredients."),
        SIDE("side", "Side", "Show another panel with dates or contact details.");

        final String key;
        final String title;
        final String direction;

        Panel(String key, String title, String direction) {
            this.key = key;
            this.title = title;
            this.direction = direction;
        }
    }

    private final SharedPreferences state;
    private final File directory;
    final String requestId;

    static ScanDraft open(Context context) {
        SharedPreferences state = context.getSharedPreferences("package-scan", Context.MODE_PRIVATE);
        String requestId = state.getString("request", null);
        return requestId == null ? null : new ScanDraft(context, state, requestId);
    }

    static ScanDraft create(Context context) throws IOException {
        SharedPreferences state = context.getSharedPreferences("package-scan", Context.MODE_PRIVATE);
        String requestId = UUID.randomUUID().toString();
        ScanDraft draft = new ScanDraft(context, state, requestId);
        if (!draft.directory.mkdirs()) throw new IOException("Photo storage could not be opened.");
        if (!state.edit().clear().putString("request", requestId).commit()) {
            draft.deletePhotos();
            throw new IOException("The camera session could not be saved.");
        }
        return draft;
    }

    private ScanDraft(Context context, SharedPreferences state, String requestId) {
        this.state = state;
        this.requestId = requestId;
        directory = new File(new File(context.getFilesDir(), "scans"), requestId);
    }

    File image(Panel panel) {
        return new File(directory, panel.key + ".jpg");
    }

    File temporaryImage(Panel panel) throws IOException {
        return File.createTempFile(panel.key + "-", ".part.jpg", directory);
    }

    private File signature(Panel panel) {
        return new File(directory, panel.key + ".luma");
    }

    void keep(Panel panel, File picture, byte[] samples) throws IOException {
        if (!picture.isFile() || picture.length() == 0) throw new IOException("The camera did not save a photo.");
        Files.write(signature(panel).toPath(), samples);
        if (!picture.renameTo(image(panel))) throw new IOException("The camera photo could not be stored.");
    }

    List<Panel> panels() {
        List<Panel> available = new ArrayList<>();
        for (Panel panel : Panel.values()) if (image(panel).isFile()) available.add(panel);
        return available;
    }

    List<byte[]> signatures() {
        List<byte[]> samples = new ArrayList<>();
        for (Panel panel : panels()) {
            try {
                samples.add(Files.readAllBytes(signature(panel).toPath()));
            } catch (IOException ignored) {
                // A missing signature leaves the JPEG usable for submission.
            }
        }
        return samples;
    }

    boolean ready() {
        return state.getBoolean("ready", false) || image(Panel.SIDE).isFile();
    }

    boolean finishCapture() {
        return state.edit().putBoolean("ready", true).commit();
    }

    String inspectionId() {
        return state.getString("inspection", "");
    }

    boolean published(String id) {
        if (!state.edit().putString("inspection", id).commit()) return false;
        deletePhotos();
        return true;
    }

    void discard() {
        state.edit().clear().commit();
        deletePhotos();
    }

    private void deletePhotos() {
        File[] children = directory.listFiles();
        if (children != null) for (File child : children) child.delete();
        directory.delete();
    }
}
