import { pgTable, serial, text, integer, timestamp } from "drizzle-orm/pg-core";
export const users = pgTable("users", {
  id: serial("id").primaryKey(), email: text("email").notNull().unique(),
  passwordHash: text("password_hash").notNull(), role: text("role").notNull().default("member"),
});
export const ledger = pgTable("ledger", {
  id: serial("id").primaryKey(), userId: integer("user_id").notNull(),
  amountSatang: integer("amount_satang").notNull(), createdAt: timestamp("created_at").defaultNow().notNull(),
});
