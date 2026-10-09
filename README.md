# loucas-por-tutoriais

Bastidores do conteúdo diário do @loucasportutoriais.

- `pedidos/AAAA-MM-DD.json`: lista de fotos do dia (matérias, imagens diretas e prompts de IA)
- `fotos/AAAA-MM-DD/`: fotos baixadas e geradas pela automação, com `status.json`
- `baixar.py` + `.github/workflows/fotos.yml`: automação que roda a cada pedido novo
- `render/render.py`: renderizador de carrosséis, reels e stories

Imagens IA usam o secret `GEMINI_API_KEY` (Settings > Secrets and variables > Actions).
