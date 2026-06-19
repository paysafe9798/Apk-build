package com.primeshani.sensi;

import android.app.Activity;
import android.content.Context;
import android.os.BatteryManager;
import android.os.Build;
import android.util.DisplayMetrics;
import android.view.Display;
import android.view.WindowManager;

import org.json.JSONObject;

/**
 * Collects real, on-device hardware/display/battery info automatically.
 * No manual entry required — this is what feeds the sensitivity engine.
 */
public class DeviceCollector {

    public static JSONObject collect(Activity activity) {
        JSONObject o = new JSONObject();
        try {
            o.put("brand", Build.BRAND == null ? "unknown" : Build.BRAND);
            o.put("manufacturer", Build.MANUFACTURER == null ? "unknown" : Build.MANUFACTURER);
            o.put("model", Build.MODEL == null ? "unknown" : Build.MODEL);
            o.put("device", Build.DEVICE == null ? "unknown" : Build.DEVICE);
            o.put("hardware", Build.HARDWARE == null ? "unknown" : Build.HARDWARE);
            o.put("board", Build.BOARD == null ? "unknown" : Build.BOARD);
            o.put("android_ver", Build.VERSION.RELEASE == null ? "unknown" : Build.VERSION.RELEASE);
            o.put("sdk", String.valueOf(Build.VERSION.SDK_INT));

            // RAM
            android.app.ActivityManager am =
                    (android.app.ActivityManager) activity.getSystemService(Context.ACTIVITY_SERVICE);
            android.app.ActivityManager.MemoryInfo mi = new android.app.ActivityManager.MemoryInfo();
            am.getMemoryInfo(mi);
            double ramGb = mi.totalMem / (1024.0 * 1024.0 * 1024.0);
            o.put("ram_gb", Math.round(ramGb * 10.0) / 10.0);

            // Display: resolution, density, refresh rate
            WindowManager wm = (WindowManager) activity.getSystemService(Context.WINDOW_SERVICE);
            Display display = wm.getDefaultDisplay();
            DisplayMetrics dm = new DisplayMetrics();
            display.getRealMetrics(dm);
            o.put("screen_w", dm.widthPixels);
            o.put("screen_h", dm.heightPixels);
            o.put("dpi", (int) dm.densityDpi);
            float refresh = display.getRefreshRate();
            o.put("refresh_hz", (int) Math.round(refresh));

            // Battery
            BatteryManager bm = (BatteryManager) activity.getSystemService(Context.BATTERY_SERVICE);
            int level = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
            o.put("battery", level >= 0 ? level : 100);

            // CPU cores (proxy for load context, kept simple/no-root)
            o.put("load_avg", 0.0);
            o.put("touch_hz", 0); // not exposed without root; engine treats 0 as "unknown"

        } catch (Exception e) {
            // leave defaults on failure
        }
        return o;
    }
}
