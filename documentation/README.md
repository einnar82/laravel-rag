# Laravel RAG Documentation

Detailed technical documentation for the Laravel RAG system.

> **Note**: This is the project documentation folder. Laravel documentation sources are cached in `sources/` (not tracked in git).

## Documentation Index

### 📖 Getting Started
- [Main README](../README.md) - Project overview and quick start
- [Quick Start Guide](QUICKSTART.md) - 10-minute setup guide
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues and solutions

### 🔧 Technical Documentation
- [API Reference](API.md) - Complete REST API documentation
- [Architecture](ARCHITECTURE.md) - System design, components, and data flow
- [Deployment](DEPLOYMENT.md) - Production deployment and scaling

### 📝 Development
- [Project Instructions](../claude.md) - Claude AI development guidelines
- [Configuration](../config/system.yaml) - System configuration reference

## Quick Links

### Common Tasks
- **Setup**: See [QUICKSTART.md](QUICKSTART.md)
- **API Usage**: See [API.md](API.md#endpoints)
- **Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md#production-deployment)
- **Issues**: See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Code Structure
```
src/
├── api/              # FastAPI REST endpoints
├── cli/              # CLI commands
├── extraction/       # Document parsing
├── indexing/         # Embeddings & vector store
├── retrieval/        # RAG chain
└── utils/            # Utilities & logging
```

## Contributing

When adding new documentation:
1. Keep user-facing docs in the root (`README.md`, `QUICKSTART.md`)
2. Keep technical details in `documentation/` (API, architecture, deployment)
3. Update this index when adding new docs
4. Use clear headings and examples
5. Link between documents for easy navigation

## Support

For questions or issues:
1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) first
2. Review relevant technical docs
3. Open an issue on GitHub
