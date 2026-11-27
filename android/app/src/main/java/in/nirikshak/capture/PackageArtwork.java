package in.nirikshak.capture;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Shader;
import android.view.View;

/** Illustrates the package and the four corners of the camera guide. */
final class PackageArtwork extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path face = new Path();
    private final Shader front = new LinearGradient(-38, -16, 39, 54, 0xffa8c997, 0xff5b8c70, Shader.TileMode.CLAMP);
    private final Shader side = new LinearGradient(0, 0, 57, 28, 0xff6a9b7b, 0xff2e594a, Shader.TileMode.CLAMP);

    PackageArtwork(Context context) {
        super(context);
        setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);
    }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        float scale = Math.min(getWidth() / 300f, getHeight() / 144f);
        canvas.save();
        canvas.translate(getWidth() / 2f, getHeight() / 2f);
        canvas.scale(scale, scale);

        fill(0xff273a30);
        for (int x = -132; x <= 132; x += 12) {
            for (int y = -60; y <= 60; y += 12) {
                canvas.drawCircle(x, y, 0.9f, paint);
            }
        }
        fill(0xff172d25);
        canvas.drawOval(-69, 43, 71, 63, paint);

        polygon(canvas, 0xffd0e2ae, null, -53, -29, 4, -56, 55, -34, 0, -7);
        polygon(canvas, Color.WHITE, front, -53, -29, 0, -7, 0, 55, -53, 33);
        polygon(canvas, Color.WHITE, side, 0, -7, 55, -34, 55, 28, 0, 55);
        polygon(canvas, 0xffedebc4, null, -36, -38, 17, -15, 27, -20, -26, -43);
        polygon(canvas, 0xffe0dcad, null, 17, -15, 27, -20, 27, -5, 17, 0);

        polygon(canvas, 0xffdeebca, null, -44, -8, -10, 6, -10, 36, -44, 22);
        paint.setColor(0xff3d6453);
        paint.setStrokeWidth(1.5f);
        for (int i = 0; i < 6; i++) {
            float x = -38 + i * 3.9f;
            float y = 1 + i * 1.6f;
            canvas.drawLine(x, y, x, y + 11, paint);
        }
        canvas.drawLine(-38, 17, -18, 25, paint);

        paint.setStrokeWidth(1.6f);
        paint.setColor(0xffb0dc9e);
        paint.setStrokeCap(Paint.Cap.ROUND);
        for (int horizontal = -1; horizontal <= 1; horizontal += 2) {
            for (int vertical = -1; vertical <= 1; vertical += 2) {
                float x = horizontal * 86f;
                float y = vertical * 60f;
                canvas.drawLine(x, y, x - horizontal * 13f, y, paint);
                canvas.drawLine(x, y, x, y - vertical * 13f, paint);
            }
        }
        fill(0xffc5ef92);
        canvas.drawCircle(105, -41, 2.4f, paint);
        canvas.restore();
    }

    private void fill(int color) {
        paint.setStyle(Paint.Style.FILL);
        paint.setColor(color);
        paint.setShader(null);
    }

    private void polygon(Canvas canvas, int color, Shader shader,
                         float x0, float y0, float x1, float y1, float x2, float y2, float x3, float y3) {
        fill(color);
        paint.setShader(shader);
        face.reset();
        face.moveTo(x0, y0);
        face.lineTo(x1, y1);
        face.lineTo(x2, y2);
        face.lineTo(x3, y3);
        face.close();
        canvas.drawPath(face, paint);
        paint.setShader(null);
    }
}
