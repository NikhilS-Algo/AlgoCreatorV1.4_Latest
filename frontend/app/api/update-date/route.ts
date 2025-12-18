import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function POST(request: Request) {
  const payload = await request.json();

const filePath = path.join(process.cwd(), "data/retrieval.json");
const rawData = fs.readFileSync(filePath, "utf8");

  const json = JSON.parse(rawData);

  if (!json.date_range) json.date_range = {};

  const allowedFields = [
    "creation_start",
    "creation_end",
    "modification_start",
    "modification_end",
  ];

  for (const field of allowedFields) {
    if (payload[field]) {
      json.date_range[field] = payload[field];
    }
  }

  fs.writeFileSync(filePath, JSON.stringify(json, null, 2), "utf8");

  return NextResponse.json({ success: true, updated: json.date_range });
}
