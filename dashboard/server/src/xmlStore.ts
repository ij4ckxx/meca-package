import AdmZip from "adm-zip";
import { getArticleFile } from "./dataStore.js";

const XML_SUFFIX_BY_KIND: Record<string, string> = {
  raw: "_raw.xml",
  article: "_article.xml",
  transfer: "_transfer.xml",
  manifest: "_manifest.xml",
  reviews: "_reviews.xml",
};

export const XML_KINDS = Object.keys(XML_SUFFIX_BY_KIND);

/** Extracts one of the 5 generated XML documents directly out of the already-built MECA zip. */
export function getArticleXml(
  batchId: string,
  articleId: string,
  kind: string,
): { name: string; data: Buffer } | null {
  const suffix = XML_SUFFIX_BY_KIND[kind];
  if (!suffix) return null;

  const zipPath = getArticleFile(batchId, articleId, "zip");
  if (!zipPath) return null;

  const zip = new AdmZip(zipPath);
  const entry = zip.getEntries().find((e) => e.entryName.endsWith(suffix));
  if (!entry) return null;

  return { name: entry.entryName, data: entry.getData() };
}
