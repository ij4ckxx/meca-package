import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

/** <repo>/meca-engine — three levels up from dashboard/server/src/. */
export const MECA_ENGINE_ROOT = join(__dirname, "../../../meca-engine");

/** <repo>/archive_migration_validation, overridable for local experimentation. */
export const DATA_ROOT =
  process.env.DASHBOARD_DATA_ROOT ?? join(__dirname, "../../../archive_migration_validation");

export const BATCHES_ROOT = join(DATA_ROOT, "batches");
