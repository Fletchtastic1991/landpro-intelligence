import express from "express";

const app = express();
app.use(express.json());

app.get("/test", (req, res) => {
  res.json({ status: "LandPro OS is alive" });
});

app.listen(3001, () => console.log("Server running on port 3001"));
