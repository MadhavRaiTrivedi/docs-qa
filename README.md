# Docs Q&A

A question-answering service over a team's own documents: upload PDFs and Markdown files, ask questions in plain language, and get answers that cite the exact file, page and passage they came from.

## Why I built it

Teams keep policies, runbooks and guides in files that nobody can search well. Keyword search fails as soon as the question uses different words from the document, and a general chatbot will happily make up a policy that does not exist.

Retrieval-Augmented Generation (RAG) fixes this by finding the relevant passages first and letting an LLM answer only from them. Getting it to work on a demo is easy; getting it to be trustworthy is not. I built this project to learn the parts that decide whether a RAG system can be trusted: how documents are chunked, why hybrid search beats pure vector search, how to make every claim traceable to a source, how to say "I don't know", and how to measure retrieval and answer quality instead of judging by eye.

## Status

Requirements and domain model are written. Implementation has not started yet.

- [Requirements](docs/requirements.md): scope, functional and non-functional requirements, and the decisions taken so far.
- [Domain model](docs/domain-model.md): core types, the document lifecycle, and how ingestion and question answering work step by step.

## Planned features

- Collections of documents, with PDF, Markdown and plain text upload
- Background ingestion: parsing, chunking and embedding, with status and retry
- Duplicate uploads detected by content hash, and document replacement without downtime
- Hybrid search: vector similarity and full-text search merged with Reciprocal Rank Fusion
- Answers from Claude with claim-level citations to file, page and passage
- An explicit "not in the documents" answer when nothing relevant is found
- Streaming answers over Server-Sent Events
- Answer ratings, and a trace of every question (retrieved chunks, tokens, latency)
- An evaluation command reporting hit rate, MRR and faithfulness on a fixed question set

## Planned stack

Python, FastAPI, PostgreSQL with pgvector, Ollama for local embeddings, the Claude API for answers, Docker. Each choice will be explained in a tech stack table once it is in the code.
