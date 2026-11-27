package in.nirikshak.capture;

import androidx.lifecycle.LiveData;
import androidx.lifecycle.MutableLiveData;
import androidx.lifecycle.ViewModel;

import org.json.JSONObject;

import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class SubmissionModel extends ViewModel {
    record Progress(String requestId, String message, JSONObject result, Exception failure) {
        boolean active() {
            return result == null && failure == null;
        }
    }

    private final MutableLiveData<Progress> progress = new MutableLiveData<>();
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final InspectionApi api = new InspectionApi(BuildConfig.API_BASE);

    LiveData<Progress> progress() {
        return progress;
    }

    Progress current(ScanDraft draft) {
        Progress value = progress.getValue();
        return draft != null && value != null && draft.requestId.equals(value.requestId()) ? value : null;
    }

    void submit(ScanDraft draft) {
        Progress current = current(draft);
        if (current != null && current.active()) return;
        progress.setValue(new Progress(draft.requestId, "Preparing captured photos…", null, null));
        executor.execute(() -> {
            try {
                JSONObject saved = api.submit(draft,
                        message -> progress.postValue(new Progress(draft.requestId, message, null, null)));
                if (!draft.published(saved.getString("id"))) throw new IOException("Could not save the inspection on this phone.");
                progress.postValue(new Progress(draft.requestId, "", saved, null));
            } catch (Exception failure) {
                progress.postValue(new Progress(draft.requestId, "", null, failure));
            }
        });
    }

    @Override protected void onCleared() {
        executor.shutdown();
    }
}
