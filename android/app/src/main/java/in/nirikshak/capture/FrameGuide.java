package in.nirikshak.capture;

import java.util.ArrayList;
import java.util.List;

/** Measures a small upright luma sample of the live viewfinder. */
final class FrameGuide {
    static final int WIDTH = 48;
    static final int HEIGHT = 64;
    static final int REQUIRED_STABLE_FRAMES = 6;

    enum Prompt {
        MOVE_CLOSER("Move closer to the packet"),
        MOVE_LEFT("Move the camera left"),
        MOVE_RIGHT("Move the camera right"),
        MOVE_UP("Move the camera up"),
        MOVE_DOWN("Move the camera down"),
        MORE_LIGHT("Move the packet into better light"),
        GLARE("Tilt the packet to reduce glare"),
        FOCUS("Hold still so the camera can focus"),
        NEXT_PANEL("Turn to a different panel"),
        STEADY("Hold steady");

        final String message;

        Prompt(String message) {
            this.message = message;
        }
    }

    record Reading(Prompt prompt, int stableFrames) {
        boolean ready() {
            return stableFrames >= REQUIRED_STABLE_FRAMES;
        }
    }

    private final List<byte[]> captured = new ArrayList<>();
    private byte[] previous;
    private int stable;

    FrameGuide(List<byte[]> capturedSamples) {
        for (byte[] sample : capturedSamples) {
            if (sample.length == WIDTH * HEIGHT) captured.add(sample);
        }
    }

    Reading measure(byte[] samples) {
        int light = 0;
        int clipped = 0;
        int edges = 0;
        int centralEdges = 0;
        double edgeX = 0;
        double edgeY = 0;
        double sharpness = 0;
        int contentCells = 0;
        int glareCells = 0;
        int[] glare = new int[16];
        int[] texture = new int[16];
        for (int y = HEIGHT / 8; y < HEIGHT * 7 / 8; y++) {
            for (int x = WIDTH / 8; x < WIDTH * 7 / 8; x++) {
                int i = y * WIDTH + x;
                int center = Byte.toUnsignedInt(samples[i]);
                int vx = Byte.toUnsignedInt(samples[i + 1]) - Byte.toUnsignedInt(samples[i - 1]);
                int vy = Byte.toUnsignedInt(samples[i + WIDTH]) - Byte.toUnsignedInt(samples[i - WIDTH]);
                int cell = (y - HEIGHT / 8) / 12 * 4 + (x - WIDTH / 8) / 9;
                light += center;
                if (center >= 249) {
                    clipped++;
                    glare[cell]++;
                }
                int laplacian = Byte.toUnsignedInt(samples[i - 1]) + Byte.toUnsignedInt(samples[i + 1])
                        + Byte.toUnsignedInt(samples[i - WIDTH]) + Byte.toUnsignedInt(samples[i + WIDTH]) - 4 * center;
                sharpness += laplacian * laplacian;
                if (Math.abs(vx) + Math.abs(vy) > 28) {
                    edges++;
                    texture[cell]++;
                    edgeX += x;
                    edgeY += y;
                    if (x >= WIDTH / 4 && x < WIDTH * 3 / 4 && y >= HEIGHT / 4 && y < HEIGHT * 3 / 4) centralEdges++;
                }
                contentCells++;
            }
        }
        int texturedCells = 0;
        for (int i = 0; i < texture.length; i++) {
            if (texture[i] >= 9) texturedCells++;
            if (glare[i] >= 86 && texture[i] < 7) glareCells++;
        }

        Prompt issue = null;
        double mean = (double) light / contentCells;
        if (mean < 54) issue = Prompt.MORE_LIGHT;
        else if (clipped > contentCells * .75 || (glareCells >= 2 && mean < 190 && clipped > contentCells * .13)) {
            issue = Prompt.GLARE;
        } else if (edges >= 40 && captured.stream().anyMatch(prior -> samePanel(samples, prior))) issue = Prompt.NEXT_PANEL;
        else if (edges >= 40 && edgeX / edges < WIDTH * .36) issue = Prompt.MOVE_LEFT;
        else if (edges >= 40 && edgeX / edges > WIDTH * .64) issue = Prompt.MOVE_RIGHT;
        else if (edges >= 40 && edgeY / edges < HEIGHT * .36) issue = Prompt.MOVE_UP;
        else if (edges >= 40 && edgeY / edges > HEIGHT * .64) issue = Prompt.MOVE_DOWN;
        else if (edges < contentCells * .06 || centralEdges < 35 || texturedCells < 7) issue = Prompt.MOVE_CLOSER;
        else if (sharpness / contentCells < 270) issue = Prompt.FOCUS;

        boolean still = previous != null && meanDifference(samples, previous, false) < 8;
        previous = samples;
        stable = issue == null ? (still ? Math.min(stable + 1, REQUIRED_STABLE_FRAMES) : 1) : 0;
        return new Reading(issue == null ? Prompt.STEADY : issue, stable);
    }

    private static long hash(byte[] samples) {
        long hash = 0;
        for (int y = 0; y < 8; y++) {
            int previous = average(samples, 4, 4 + y * 7);
            for (int x = 1; x <= 8; x++) {
                int current = average(samples, 4 + x * 5, 4 + y * 7);
                hash = (hash << 1) | (previous < current ? 1 : 0);
                previous = current;
            }
        }
        return hash;
    }

    private static int average(byte[] samples, int x, int y) {
        int sum = 0;
        for (int row = y - 2; row <= y + 2; row++) {
            for (int col = x - 2; col <= x + 2; col++) {
                sum += Byte.toUnsignedInt(samples[row * WIDTH + col]);
            }
        }
        return sum;
    }

    private static boolean samePanel(byte[] first, byte[] second) {
        int hashDistance = Long.bitCount(hash(first) ^ hash(second));
        double difference = meanDifference(first, second, true);
        return difference < 17 || (hashDistance <= 12 && difference < 34);
    }

    private static double meanDifference(byte[] first, byte[] second, boolean removeExposureShift) {
        int sum = 0;
        if (removeExposureShift) {
            for (int i = 0; i < first.length; i++) {
                sum += Byte.toUnsignedInt(first[i]) - Byte.toUnsignedInt(second[i]);
            }
        }
        double shift = (double) sum / first.length;
        double difference = 0;
        for (int i = 0; i < first.length; i++) {
            difference += Math.abs(Byte.toUnsignedInt(first[i]) - Byte.toUnsignedInt(second[i]) - shift);
        }
        return difference / first.length;
    }
}
