import express from "express";
import cors from "cors";
import { router } from "./routes.js";

const app = express();
const PORT = process.env.PORT ? Number(process.env.PORT) : 4000;

app.use(cors());
app.use(express.json());
app.use("/api", router);

app.listen(PORT, () => {
  console.log(`Dashboard API listening on http://localhost:${PORT}`);
});
