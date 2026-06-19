package com.primeshani.sensi;

import android.os.Bundle;
import android.view.animation.AnimationUtils;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONObject;

public class MainActivity extends AppCompatActivity {

    private TextView tvDeviceName, tvTier, tvPower, tvResult;
    private ProgressBar progressBar;
    private Button btnGenerate;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }

        tvDeviceName = findViewById(R.id.tvDeviceName);
        tvTier = findViewById(R.id.tvTier);
        tvPower = findViewById(R.id.tvPower);
        tvResult = findViewById(R.id.tvResult);
        progressBar = findViewById(R.id.progressBar);
        btnGenerate = findViewById(R.id.btnGenerate);

        btnGenerate.setOnClickListener(v -> generateSensitivity());

        // Auto-run once on launch so results are ready immediately
        generateSensitivity();
    }

    private void generateSensitivity() {
        btnGenerate.setEnabled(false);
        progressBar.setVisibility(android.view.View.VISIBLE);
        tvResult.setText("");

        new Thread(() -> {
            try {
                // 1. Auto-collect real device data (no manual input)
                JSONObject deviceJson = DeviceCollector.collect(this);

                // 2. Hand off to the Python engine (same logic as desktop tool)
                Python py = Python.getInstance();
                PyObject engine = py.getModule("engine");

                PyObject device = engine.callAttr("get_device"); // fallback path
                // Override with real collected values via a small python-side updater
                PyObject result = engine.callAttr(
                        "run_full",
                        deviceJson.toString()
                );

                String resultText = result.toString();

                runOnUiThread(() -> {
                    tvResult.setText(resultText);
                    tvResult.setAnimation(AnimationUtils.loadAnimation(this, android.R.anim.fade_in));
                    progressBar.setVisibility(android.view.View.GONE);
                    btnGenerate.setEnabled(true);
                });

            } catch (Exception e) {
                runOnUiThread(() -> {
                    tvResult.setText("Error: " + e.getMessage());
                    progressBar.setVisibility(android.view.View.GONE);
                    btnGenerate.setEnabled(true);
                });
            }
        }).start();
    }
}
