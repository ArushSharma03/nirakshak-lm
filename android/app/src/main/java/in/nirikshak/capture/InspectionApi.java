package in.nirikshak.capture;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.UUID;
import java.util.Locale;
import java.util.function.Consumer;

final class InspectionApi {
    private static final int READ_TIMEOUT = 30_000;
    private static final int ANALYSIS_TIMEOUT = 10 * 60_000;
    private final String base;

    InspectionApi(String base) {
        this.base = base.replaceAll("/+$", "");
    }

    JSONObject submit(ScanDraft draft, Consumer<String> status) throws IOException, JSONException {
        status.accept("Connecting to the inspection server…");
        JSONObject record = json("POST", "/inspections/",
                new JSONObject().put("client_request_id", draft.requestId).toString(), READ_TIMEOUT);
        String path = "/inspections/" + record.getString("id");
        for (ScanDraft.Panel panel : draft.panels()) {
            File image = draft.image(panel);
            JSONObject images = record.optJSONObject("images");
            JSONObject saved = images == null ? null : images.optJSONObject(panel.key);
            if (saved != null && saved.optString("file_hash").equals(sha256(image))) continue;
            status.accept("Sending the " + panel.title.toLowerCase(java.util.Locale.ROOT) + " photo…");
            record = upload(path + "/images", panel, image);
        }
        if (record.optJSONObject("analysis") != null) return record;

        status.accept("Reading the label and checking declarations…");
        long waitUntil = System.nanoTime() + java.util.concurrent.TimeUnit.MINUTES.toNanos(5);
        for (long delay = 2000; ; delay = Math.min(delay * 2, 12_000)) {
            try {
                return json("POST", path + "/analyze", "{\"use_jev\":false}", ANALYSIS_TIMEOUT);
            } catch (ApiError error) {
                if (error.code != 409 || !error.getMessage().toLowerCase(Locale.ROOT).contains("already running")
                        || System.nanoTime() >= waitUntil) throw error;
                status.accept("The analysis server is busy. Waiting to retry…");
                try {
                    Thread.sleep(delay);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    throw new IOException("Analysis was interrupted.", interrupted);
                }
                record = json("GET", path, null, READ_TIMEOUT);
                if (record.optJSONObject("analysis") != null) return record;
            } catch (IOException error) {
                try {
                    record = json("GET", path, null, READ_TIMEOUT);
                    if (record.optJSONObject("analysis") != null) return record;
                } catch (IOException ignored) {
                    // Report the original error. The next retry checks the server again.
                }
                throw error;
            }
        }
    }

    JSONObject inspection(String id) throws IOException, JSONException {
        return json("GET", "/inspections/" + id, null, READ_TIMEOUT);
    }

    String report(String id) throws IOException {
        return request("GET", "/inspections/" + id + "/report?download=false", null, 0, null, READ_TIMEOUT);
    }

    private JSONObject json(String method, String path, String content, int timeout) throws IOException, JSONException {
        byte[] body = content == null ? null : content.getBytes(StandardCharsets.UTF_8);
        return new JSONObject(request(method, path, "application/json", body == null ? 0 : body.length,
                body == null ? null : output -> output.write(body), timeout));
    }

    private JSONObject upload(String path, ScanDraft.Panel panel, File image) throws IOException, JSONException {
        String boundary = "nirikshak-" + UUID.randomUUID();
        byte[] header = ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"view_type\"\r\n\r\n"
                + panel.key + "\r\n--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; filename=\""
                + panel.key + ".jpg\"\r\nContent-Type: image/jpeg\r\n\r\n").getBytes(StandardCharsets.UTF_8);
        byte[] footer = ("\r\n--" + boundary + "--\r\n").getBytes(StandardCharsets.UTF_8);
        return new JSONObject(request("POST", path, "multipart/form-data; boundary=" + boundary,
                header.length + image.length() + footer.length, output -> {
                    output.write(header);
                    Files.copy(image.toPath(), output);
                    output.write(footer);
                }, READ_TIMEOUT));
    }

    private String request(String method, String path, String type, long length, Body body, int timeout) throws IOException {
        if (base.isEmpty()) throw new IOException("This build needs an HTTPS inspection server.");
        HttpURLConnection connection = (HttpURLConnection) new URL(base + path).openConnection();
        try {
            connection.setRequestMethod(method);
            connection.setConnectTimeout(10_000);
            connection.setReadTimeout(timeout);
            connection.setInstanceFollowRedirects(false);
            if (body != null) {
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", type);
                connection.setFixedLengthStreamingMode(length);
                try (OutputStream output = connection.getOutputStream()) {
                    body.write(output);
                }
            }
            int code = connection.getResponseCode();
            boolean success = code >= 200 && code < 300;
            try (InputStream stream = success ? connection.getInputStream() : connection.getErrorStream()) {
                String content = stream == null ? "" : read(stream);
                if (!success) throw new ApiError(code, content);
                return content;
            }
        } finally {
            connection.disconnect();
        }
    }

    private static String read(InputStream stream) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] buffer = new byte[8192];
        int count;
        while ((count = stream.read(buffer)) != -1) output.write(buffer, 0, count);
        return new String(output.toByteArray(), StandardCharsets.UTF_8);
    }

    private static String sha256(File file) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (DigestInputStream stream = new DigestInputStream(Files.newInputStream(file.toPath()), digest)) {
                byte[] buffer = new byte[8192];
                while (stream.read(buffer) != -1) {
                    // DigestInputStream updates the digest while reading.
                }
            }
            StringBuilder result = new StringBuilder(64);
            for (byte value : digest.digest()) result.append(String.format(java.util.Locale.ROOT, "%02x", value & 0xff));
            return result.toString();
        } catch (NoSuchAlgorithmException error) {
            throw new IOException("Unable to verify the photo.", error);
        }
    }

    private interface Body {
        void write(OutputStream output) throws IOException;
    }

    private static final class ApiError extends IOException {
        final int code;

        ApiError(int code, String response) {
            super(detail(code, response));
            this.code = code;
        }

        private static String detail(int code, String response) {
            try {
                Object detail = new JSONObject(response).opt("detail");
                if (detail instanceof String message) return message;
            } catch (JSONException ignored) {
                // HTML proxy errors should not be shown directly in the app.
            }
            return "The inspection server returned HTTP " + code + ".";
        }
    }
}
