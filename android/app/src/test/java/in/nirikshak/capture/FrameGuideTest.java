package in.nirikshak.capture;

import org.junit.Test;

import java.util.Arrays;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class FrameGuideTest {
    private static final int WIDTH = FrameGuide.WIDTH;
    private static final int HEIGHT = FrameGuide.HEIGHT;

    @Test
    public void waitsForAStableFrameSequenceAndResetsAfterMovement() {
        var guide = new FrameGuide(List.of());
        byte[] front = panel(false, 0);
        byte[] back = panel(true, 0);
        for (int i = 1; i < FrameGuide.REQUIRED_STABLE_FRAMES; i++) {
            assertFalse(guide.measure(front).ready());
        }
        assertTrue(guide.measure(front).ready());
        var moved = guide.measure(back);
        assertFalse(moved.ready());
        assertEquals(1, moved.stableFrames());
        for (int i = 1; i < FrameGuide.REQUIRED_STABLE_FRAMES - 1; i++) guide.measure(back);
        assertTrue(guide.measure(back).ready());
    }

    @Test
    public void rejectsSamePanelAfterExposureShiftAndAcceptsDifferentPanel() {
        var guide = new FrameGuide(List.of(panel(false, 0)));
        for (int i = 0; i < 8; i++) {
            var reading = guide.measure(panel(false, 22));
            assertEquals(FrameGuide.Prompt.NEXT_PANEL, reading.prompt());
            assertFalse(reading.ready());
        }
        FrameGuide.Reading back = null;
        for (int i = 0; i < FrameGuide.REQUIRED_STABLE_FRAMES; i++) back = guide.measure(panel(true, 0));
        assertTrue(back.ready());
    }

    @Test
    public void requestsBetterLightingAndFraming() {
        var guide = new FrameGuide(List.of());
        assertEquals(FrameGuide.Prompt.MORE_LIGHT, guide.measure(flat(30)).prompt());
        assertEquals(FrameGuide.Prompt.GLARE, guide.measure(flat(252)).prompt());
        assertEquals(FrameGuide.Prompt.MOVE_CLOSER, guide.measure(flat(125)).prompt());
        byte[] left = flat(125);
        byte[] textured = panel(true, 0);
        for (int row = 0; row < HEIGHT; row++) System.arraycopy(textured, row * WIDTH, left, row * WIDTH, WIDTH / 3);
        assertEquals(FrameGuide.Prompt.MOVE_LEFT, guide.measure(left).prompt());
    }

    private static byte[] flat(int luminance) {
        byte[] pixels = new byte[WIDTH * HEIGHT];
        Arrays.fill(pixels, (byte) luminance);
        return pixels;
    }

    private static byte[] panel(boolean horizontal, int exposure) {
        byte[] pixels = new byte[WIDTH * HEIGHT];
        for (int y = 0; y < HEIGHT; y++) {
            for (int x = 0; x < WIDTH; x++) {
                int band = horizontal ? y / 3 : x / 3;
                pixels[y * WIDTH + x] = (byte) ((band % 2 == 0 ? 65 : 183) + exposure);
            }
        }
        return pixels;
    }
}
