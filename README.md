# Trace AI: Socratic Code Mentorship Swarm

![Trace AI Demo](https://img.shields.io/badge/Status-Live_Demo-success) ![License](https://img.shields.io/badge/License-MIT-blue) ![NVIDIA](https://img.shields.io/badge/Powered_by-NVIDIA_Nemotron-76B900) ![Nebius](https://img.shields.io/badge/Hosted_on-Nebius_Token_Factory-8B5CF6)

**Trace AI** is an intelligent, agentic swarm platform designed to teach algorithmic problem-solving. Instead of traditional AI wrappers that simply output the correct code, Trace AI acts as a strict Socratic mentor. It utilizes a 3-layer hardened execution sandbox and dynamically routes tasks across NVIDIA Nemotron models to diagnose logical flaws, generate adversarial edge cases, and guide the learner to the "aha" moment—all while optimizing token usage by over 80%.

---

## 🧠 NVIDIA Nemotron & Nebius Token Factory Integration

This project was built specifically to leverage the power of **NVIDIA open-source models** hosted on the **Nebius Token Factory**.

### Model Orchestration Strategy
We engineered a multi-model agentic swarm that dynamically routes tasks based on computational complexity:

1. **`NVIDIA-Nemotron-3-Nano-30B-A3B`**
   * **Role:** High-speed, low-latency generation.
   * **Implementation:** Used for autonomous adversarial edge-case generation before code execution, "Smart Import" problem parsing, and foundational Level-1 hints. Its smaller footprint prevents wasting expensive compute on simple logic operations.
2. **`nemotron-3-super-120b-a12b`**
   * **Role:** Deep reasoning and Socratic deduction.
   * **Implementation:** Reserved for computationally heavy tasks. It analyzes failed execution traces from the sandbox, diagnoses deep logical misconceptions (e.g., "Boundary - Method signature misuse"), and powers the multi-turn Socratic Mentor chat.

### How Nebius Accelerated Our Workflow
* **Nebius Token Factory:** Accelerated our backend development by providing highly reliable, OpenAI-compatible API endpoints. The immense throughput allowed us to run parallel swarm calls (e.g., generating edge cases while simultaneously analyzing public test failures) without hitting rate limits or timeouts.
* **Token Optimization & Telemetry:** We utilized Nebius usage metrics to implement aggressive "Short-Circuiting." If user code passes all tests perfectly, or violates our AST security gate, we completely bypass the Super-120B model, achieving an average **~82% API token cost savings** per evaluation cycle.

---

## ✨ Key Features

* **Agentic Multi-Model Routing:** Intelligently splits workloads between Nemotron Nano and Super.
* **Hardened 3-Layer Sandbox:** Secure local Python execution featuring:
  1. *Static AST Parsing:* Blocks malicious imports and built-ins before execution.
  2. *Sanitized Subprocesses:* Strips host secrets (like `NEBIUS_API_KEY`) from memory.
  3. *OS-Level Limits:* Caps CPU and RAM usage to prevent resource exhaustion.
* **Smart Import:** Frictionless LeetCode problem fetching via Nano-30B.
* **Stateful Client Caching:** React frontend caches hint levels to prevent duplicate LLM API calls.

---

## 🚀 Setup Instructions

### Prerequisites
* Python 3.10+
* Node.js 18+
* A Nebius AI account and API Key.

### 1. Backend Setup (FastAPI)
Navigate to the backend directory and set up your Python environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:
```env
NEBIUS_API_KEY=your_nebius_token_factory_key_here
PORT=10000
```

Start the local server:
```bash
uvicorn app.main:app --reload --port 10000
```

### 2. Frontend Setup (React/Vite)
Navigate to the frontend directory:
```bash
cd frontend
npm install
```

Create a `.env` file in the `frontend/` directory (root of the frontend project):
```env
VITE_API_BASE_URL=http://localhost:10000
```

Start the development server:
```bash
npm run dev
```

---

## 🌍 Deployment Guide

* **Backend (Render / Railway):** Deploy the `backend` folder as a standard Python Web Service. Ensure the Build Command is `pip install -r requirements.txt` and the Start Command is `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Add `NEBIUS_API_KEY` to your environment variables.
* **Frontend (Netlify / Vercel):** Deploy the `frontend` folder as a static site. Set the Build Command to `npm run build` and the Publish Directory to `dist`. Add `VITE_API_BASE_URL` pointing to your live backend URL.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
