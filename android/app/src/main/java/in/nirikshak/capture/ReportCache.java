package in.nirikshak.capture;

import android.content.Context;
import android.util.AtomicFile;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.Comparator;

final class ReportCache {
    private final File directory;

    ReportCache(Context context) {
        directory = new File(context.getNoBackupFilesDir(), "reports");
    }

    String read(String key) {
        try {
            return new String(new AtomicFile(file(key)).readFully(), StandardCharsets.UTF_8);
        } catch (IOException ignored) {
            return null;
        }
    }

    void write(String key, String value) {
        AtomicFile file = new AtomicFile(file(key));
        FileOutputStream output = null;
        try {
            output = file.startWrite();
            output.write(value.getBytes(StandardCharsets.UTF_8));
            file.finishWrite(output);
        } catch (IOException ignored) {
            if (output != null) file.failWrite(output);
        }
        String extension = key.endsWith(".html") ? ".html" : ".json";
        File[] copies = directory.listFiles((dir, name) -> !name.equals("history.json") && name.endsWith(extension));
        if (copies == null || copies.length <= 12) return;
        Arrays.sort(copies, Comparator.comparingLong(File::lastModified).reversed());
        for (int i = 12; i < copies.length; i++) new AtomicFile(copies[i]).delete();
    }

    void remove(String key) {
        new AtomicFile(file(key)).delete();
    }

    private File file(String key) {
        if (!key.matches("[A-Za-z0-9_.-]{1,120}")) throw new IllegalArgumentException("Invalid cache key.");
        return new File(directory, key);
    }
}
