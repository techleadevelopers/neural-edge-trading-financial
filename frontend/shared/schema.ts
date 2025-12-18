import { pgTable, text, serial, integer, boolean, timestamp, jsonb, real } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// === TABLE DEFINITIONS ===
export const signals = pgTable("signals", {
  id: serial("id").primaryKey(),
  symbol: text("symbol").notNull(),
  signal: text("signal").notNull(), // LONG_FORTE, SHORT_FRACO, NEUTRO
  score: integer("score").notNull(), // 0-100
  probability: real("probability").notNull(),
  regime: text("regime").notNull(), // BULL, BEAR, CHOP
  rsi: real("rsi"),
  vol_z: real("vol_z"),
  upper_wick: real("upper_wick"),
  ret_15: real("ret_15"),
  cooldown_min: integer("cooldown_min"),
  entry_price: real("entry_price"),
  stop_loss: real("stop_loss"),
  target_price: real("target_price"),
  reasons: jsonb("reasons").$type<string[]>(), // Array of strings
  timestamp: timestamp("timestamp").defaultNow().notNull(),
});

export const alerts = pgTable("alerts", {
  id: serial("id").primaryKey(),
  message: text("message").notNull(),
  type: text("type").notNull(), // NEW_SIGNAL, UPGRADE
  timestamp: timestamp("timestamp").defaultNow().notNull(),
});

// === SCHEMAS ===
export const insertSignalSchema = createInsertSchema(signals).omit({ id: true, timestamp: true });
export const insertAlertSchema = createInsertSchema(alerts).omit({ id: true, timestamp: true });

// === TYPES ===
export type Signal = typeof signals.$inferSelect;
export type InsertSignal = z.infer<typeof insertSignalSchema>;
export type Alert = typeof alerts.$inferSelect;
export type InsertAlert = z.infer<typeof insertAlertSchema>;

export type SignalResponse = Signal;
export type SignalsListResponse = Signal[];

// For the frontend filters
export interface SignalQueryParams {
  minScore?: number;
  onlyStrong?: boolean;
}
