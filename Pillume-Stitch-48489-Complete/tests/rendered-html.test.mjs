import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

test("contains the Pillume dashboard shell and metadata", async () => {
  const [layout, dashboard, css] = await Promise.all([
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/Dashboard.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);

  assert.match(layout, /Pillume \| 스마트 복약 케어/);
  assert.match(layout, /<html lang="ko">/);
  assert.match(dashboard, /오늘의 복약 일정/);
  assert.match(dashboard, /제스처 무드등/);
  assert.match(dashboard, /복약 캘린더/);
  assert.match(dashboard, /알약 채우기/);
  assert.match(dashboard, /LED 색상/);
  assert.match(dashboard, /lightBrightness/);
  assert.match(dashboard, /onLabel: "1"/);
  assert.match(dashboard, /offLabel: "2"/);
  assert.match(dashboard, /emergencyLabel: "3"/);
  assert.match(dashboard, /normalizeClassLabel/);
  assert.match(dashboard, /type: "emergency_ack"/);
  assert.match(dashboard, /확인 버튼을 누를 때까지/);
  assert.match(dashboard, /Pillume AI/);
  assert.match(dashboard, /confirmAssistantDose/);
  assert.match(dashboard, /확인하고 기록/);
  assert.match(dashboard, /AI는 장치를 직접 제어하지 않으며/);
  assert.match(dashboard, /OpenAI API 키 연결/);
  assert.match(dashboard, /X-OpenAI-Key/);
  assert.match(css, /@media \(max-width: 560px\)/);
  assert.match(css, /\.assistantPanel/);
  assert.doesNotMatch(`${layout}\n${dashboard}`, /codex-preview|Your site is taking shape/);
});

test("keeps required IoT integration sources", async () => {
  const [dashboard, firmware, config, api, assistantApi, schema, standalone, pyMain, pyBle] = await Promise.all([
    readFile(new URL("../app/Dashboard.tsx", import.meta.url), "utf8"),
    readFile(
      new URL("../firmware/smart_pill_dispenser.ino", import.meta.url),
      "utf8",
    ),
    readFile(new URL("../firmware/config.h", import.meta.url), "utf8"),
    readFile(new URL("../app/api/events/route.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/api/assistant/route.ts", import.meta.url), "utf8"),
    readFile(new URL("../db/schema.ts", import.meta.url), "utf8"),
    readFile(new URL("../web-standalone/index.html", import.meta.url), "utf8"),
    readFile(new URL("../micropython/main.py", import.meta.url), "utf8"),
    readFile(new URL("../micropython/ble_library.py", import.meta.url), "utf8"),
  ]);

  assert.match(dashboard, /@teachablemachine\/image/);
  assert.match(dashboard, /requestDevice/);
  assert.match(dashboard, /ESP_SZ/);
  assert.match(firmware, /pendingDoseMask/);
  assert.match(firmware, /Preferences/);
  assert.match(firmware, /BLEDevice::init/);
  assert.doesNotMatch(firmware, /#include <WiFi\.h>/);
  assert.match(config, /BLE_DEVICE_NAME\[\] = "ESP_SZ"/);
  assert.match(api, /deviceEvents/);
  assert.match(assistantApi, /OPENAI_API_KEY/);
  assert.match(assistantApi, /x-openai-key/);
  assert.match(assistantApi, /api\.openai\.com\/v1\/responses/);
  assert.match(assistantApi, /record_manual_dose/);
  assert.match(assistantApi, /json_schema/);
  assert.doesNotMatch(dashboard + standalone, /Authorization:\s*`Bearer/);
  assert.match(schema, /sqliteTable\("device_events"/);
  assert.match(standalone, /tmImage\.load/);
  assert.match(standalone, /navigator\.bluetooth\.requestDevice/);
  assert.match(standalone, /pillume-medication-events/);
  assert.match(standalone, /sendRefill/);
  assert.match(standalone, /sendLightSettings/);
  assert.match(standalone, /lightBrightness/);
  assert.match(standalone, /value="1,2,3"/);
  assert.match(standalone, /clean===normalizeLabel\(n\.on\)\?"ON"/);
  assert.match(standalone, /normalizeLabel/);
  assert.match(standalone, /type:"emergency_ack"/);
  assert.match(standalone, /Pillume AI/);
  assert.match(standalone, /sendAssistant/);
  assert.match(standalone, /confirmAssistantDose/);
  assert.match(standalone, /activateAssistantKey/);
  assert.match(standalone, /X-OpenAI-Key/);
  const inlineScript = standalone.match(
    /<script>\s*([\s\S]*?)<\/script>\s*<\/body>/,
  );
  assert.ok(inlineScript, "standalone dashboard must include its inline script");
  assert.doesNotThrow(() => new Function(inlineScript[1]));
  assert.match(pyMain, /DISPENSER_ANGLES = \(55, 110, 165\)/);
  assert.match(pyMain, /PROXIMITY_HOLD_MS = 1000/);
  assert.match(pyMain, /def animate_blue_chase/);
  assert.match(pyMain, /def update_emergency/);
  assert.match(pyMain, /REFILL_SEQUENCE = \(55, 110, 165, 0\)/);
  assert.match(pyMain, /def advance_refill/);
  assert.match(pyMain, /class BLESimplePeripheral/);
  assert.match(pyMain, /class SSD1306_I2C/);
  assert.match(pyMain, /OLED_SDA_PIN = 21/);
  assert.match(pyMain, /OLED_SCL_PIN = 22/);
  assert.match(pyMain, /MEDICINE TIME/);
  assert.match(pyMain, /PLEASE TAKE/);
  assert.match(pyMain, /def set_light_settings/);
  assert.match(pyMain, /lightBrightness/);
  assert.match(pyMain, /def acknowledge_emergency/);
  assert.match(pyMain, /command_type == "emergency_ack"/);
  assert.doesNotMatch(pyMain, /EMERGENCY_DURATION_MS/);
  assert.match(pyBle, /class BLESimplePeripheral/);
  assert.match(pyBle, /ESP_SZ/);
  await assert.rejects(access(new URL("../app/_sites-preview", import.meta.url)));
});
