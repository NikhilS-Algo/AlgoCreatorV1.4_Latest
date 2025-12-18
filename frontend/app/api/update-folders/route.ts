import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const filePath = path.join(process.cwd(), "data/retrieval.json");

export async function POST(request: Request) {
  const payload = await request.json();
  const rawData = fs.readFileSync(filePath, "utf8");
  const json = JSON.parse(rawData);

  if (Array.isArray(payload.folder_names)) {
    json.folder_names = payload.folder_names;
  }

  fs.writeFileSync(filePath, JSON.stringify(json, null, 2), "utf8");

  return NextResponse.json({ success: true, updated: json.folder_names });
}
