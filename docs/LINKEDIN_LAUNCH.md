# LinkedIn launch package — RAG Architecture Lab

**Status:** DRAFT — do not post until the public GitHub Pages URL and tag/release are verified.  
**Research identity:** Independent open-source engineering study. No claim that a generated answer is semantically certified or that GraphRAG is better.

## Public post (Spanish, ready to customize after verification)

**¿Siempre conviene agregar más IA a un sistema RAG? Nuestros benchmarks dicen que no.**

Construí **RAG Architecture Lab**, un proyecto open source donde implemento y comparo arquitecturas Retrieval-Augmented Generation desde los fundamentos: BM25, embeddings, búsqueda híbrida RRF, reranking y recuperación con grafos.

En un benchmark con **5.183 documentos y 300 consultas** (BEIR SciFact), la búsqueda híbrida obtuvo un **MRR@10 de 0,6484**, frente a **0,6328 con BM25** y **0,6047 con dense retrieval**.

Pero el resultado más interesante apareció con el reranking: al pasar de Hybrid RRF a un cross-encoder de 50 candidatos, el MRR@10 subió de **0,6484 a 0,6615**, mientras que la latencia media local aumentó de **34,53 ms a 3.706,43 ms** en la misma configuración medida.

**Más complejidad no siempre significa mejor sistema.**

También exploré GraphRAG y encontré resultados negativos o inconclusos en estudios controlados de recuperación. Los documenté tal como salieron, con sus limitaciones.

Para hacerlo explorable, desarrollé un **observatorio React + TypeScript** que muestra métricas, arquitecturas, rutas de procedencia y citas exactas de fuentes. Sin endpoints de modelos pagados ni estadísticas inventadas.

El proyecto no pretende resolver todavía la verificación semántica de respuestas generadas: esa investigación continúa abierta.

🔎 Código: https://github.com/AlexiVion/rag-architecture-lab
🧪 Observatorio: [AGREGAR ENLACE SOLO DESPUÉS DE VALIDAR GITHUB PAGES]
📋 Metodología y resultados: https://github.com/AlexiVion/rag-architecture-lab/blob/main/docs/PORTFOLIO_RELEASE.md

Me interesa especialmente la **optimización de sistemas IA bajo límites reales de CPU, memoria y latencia**, y seguiré desarrollando esa línea con modelos más pequeños.

#RAG #ArtificialIntelligence #MachineLearning #InformationRetrieval #OpenSource

## 60–90 second demo walkthrough

00:00–00:10 — Overview: what the project measures and what it explicitly does not certify.
00:10–00:25 — Experiments: BM25 vs Hybrid RRF; explain quality/latency tradeoff and matched controls.
00:25–00:40 — Real negative GraphRAG data: GRF-00 NO-GO and GRF-01 inconclusive; do not compare different DEV cohorts directly.
00:40–01:00 — Knowledge Graph: select fictional source-linked two-hop evidence path, click original quoted edge. Explicitly label this a fixture.
01:00–01:15 — Evidence review and Methodology: source provenance, citation-syntax vs semantic-support distinction; end with GitHub repository and live viewer URL.

## Publication proof

- [ ] Research branch integrated into main
- [ ] Same-head CI run passes and source path checks pass
- [ ] Pages deployment SUCCESS and exact public URL works on desktop/mobile
- [ ] Release v0.1.0 exists and SHA is documented
- [ ] Video/screenshots captured from verified live launch build
- [ ] Replace placeholder with observed URL; do not invent it
- [ ] User posts to LinkedIn and links final URL to release issue #13

**Claims to avoid:** 'most efficient RAG', 'first GraphRAG', 'scientifically reliable answers', '10 models tested', 'real-time LLM demo', 'zero hallucinations', 'breakthrough ultra-small-model RAG'.
