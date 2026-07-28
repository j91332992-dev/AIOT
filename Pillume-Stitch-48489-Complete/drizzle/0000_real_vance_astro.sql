CREATE TABLE `device_events` (
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`device_id` text DEFAULT 'esp32-pill-01' NOT NULL,
	`type` text NOT NULL,
	`meal_slot` text,
	`dose_count` integer DEFAULT 0 NOT NULL,
	`message` text DEFAULT '' NOT NULL,
	`temperature` real,
	`humidity` real,
	`device_time` text,
	`created_at` text DEFAULT CURRENT_TIMESTAMP NOT NULL
);
