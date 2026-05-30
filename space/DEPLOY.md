# Deploy the verifier to a free Hugging Face Space

A free **CPU basic** Space is enough — the verifier is HTTP + string comparison, no GPU.
Server-side calls mean no CORS limits and full coverage (incl. the PubMed support check),
with no LLM key.

## Steps
1. Create a Space — https://huggingface.co/new-space → **SDK: Docker**, **Hardware: CPU basic (free)**.
2. Bundle the current deltasci source into the build:
   ```
   cd space && ./bundle.sh        # creates space/pkg/ from ../src + ../pyproject.toml
   ```
3. Push `app.py`, `Dockerfile`, `README.md`, and `pkg/` to the Space repo:
   ```
   git clone https://huggingface.co/spaces/<you>/deltasci-verify
   cp -R app.py Dockerfile README.md pkg deltasci-verify/
   cd deltasci-verify && git add -A && git commit -m "deltasci verifier" && git push
   ```
4. Wait for the build. Your endpoint is:
   ```
   https://<you>-deltasci-verify.hf.space/verify     (POST {"text": "..."})
   https://<you>-deltasci-verify.hf.space/            (health)
   https://<you>-deltasci-verify.hf.space/docs        (interactive)
   ```
5. Point the landing at it: set `DELTASCI_VERIFY_ENDPOINT` in `docs/index.html` to that
   `/verify` URL — the demo flips from scripted replay to a live "paste & verify" tool.

## Notes / caveats
- **Free Spaces sleep** after ~48h idle → a few-second cold start for the first visitor.
- **Shared IP rate limits**: all demo traffic exits the Space's IP, so PubMed eutils
  (3 req/s unauthenticated) can throttle under heavy load. (NCBI-key support in the verifier
  is a future improvement.) Crossref / OpenAlex are generous with the `mailto` the CLI sends.
- CORS is open in `app.py` (read-only verifier). Tighten `allow_origins` to your Pages
  origin if you prefer.
