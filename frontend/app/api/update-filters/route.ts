// app/api/update-filters/route.ts
import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const filePath = path.join(process.cwd(), "data", "retrieval.json");

export async function POST(req: Request) {
  try {
    const body = await req.json();

    // Read current JSON
    const fileData = fs.readFileSync(filePath, "utf-8");
    const json = JSON.parse(fileData);

    // Map selected_files → folder_names
    if (body.selected_files) {
      json.folder_names = body.selected_files;
    }

    // Optional: support updating date_range too
    if (body.date_range) {
      json.date_range = body.date_range;
    }

    // Save changes back to file
    fs.writeFileSync(filePath, JSON.stringify(json, null, 2));

    return NextResponse.json({ success: true, updated: json });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: String(error) },
      { status: 500 }
    );
  }
}
