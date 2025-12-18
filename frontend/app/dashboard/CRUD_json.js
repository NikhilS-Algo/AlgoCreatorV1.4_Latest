import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

export async function POST(request: Request) {
  const payload = await request.json();

  const filePath = path.join(process.cwd(), "frontend/data/retrieval.json");

  const rawData = fs.readFileSync(filePath, "utf8");
  const parseData = JSON.parse(rawData);

  if (!parseData.date_range) {
    parseData.date_range = {};
  }

  const fields = ["creation_start", "creation_end", "modification_start", "modification_end"];
  for (const field of fields) {
    if (payload[field]) {
      parseData.date_range[field] = payload[field];
    }
  }

  fs.writeFileSync(filePath, JSON.stringify(parseData, null, 2), "utf8");

  return NextResponse.json({ message: "File updated", updated: parseData.date_range });
}




// export function update_folderName(foldername: string[]) {
//   parseData.folder_names = foldername;
//   fs.writeFileSync(retrieval_path, JSON.stringify(parseData, null, 2), "utf8");
//   console.log("File updated successfully!");
// }
