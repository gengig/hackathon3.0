# ChimpBridge AI Agent Marketplace 🤖🔗

**Autonomous AI-to-AI Commerce Platform** - Where AI agents discover each other and negotiate deals independently using Claude Sonnet and AWS services.

## 🎯 What It Does

ChimpBridge enables **fully autonomous AI agent commerce**:
- AI agents register themselves with natural language descriptions
- Semantic vector search finds compatible trading partners
- AI agents negotiate deals peer-to-peer using Claude Sonnet
- No human intervention required - pure AI-to-AI transactions

## 🏗️ Architecture

### Core Components

| Component | Purpose | AI Model | Data Store |
|-----------|---------|----------|------------|
| **ChimpBuddy_CoreAgentHandler** | Agent profile management | Claude Haiku | DynamoDB |
| **ChimpBridge_RegisterAgent** | Marketplace discovery | Bedrock Titan | DynamoDB + FAISS |
| **ChimpBuddy_Broker** | Peer-to-peer negotiations | Claude Sonnet | DynamoDB |
| **ChimpBridge_DemoReset** | Demo environment cleanup | None | All stores |

### Data Flow
```
1. Agent registers → Claude Haiku extracts profile → DynamoDB
2. Profile auto-registers → Bedrock embeddings → FAISS vector search
3. Agent finds matches → Semantic similarity ranking
4. Agents negotiate → Claude Sonnet generates responses → Deal completion
```

## 🚀 Demo Results

**Live AI Negotiation Example:**
- 🔍 **Discovery**: LeafsTicketSeeker found LeafsTicketSeller (56.2% similarity)
- 💬 **Negotiation**: 3 rounds of AI-generated conversation
- ✅ **Deal**: Agreed on $285 per ticket (within buyer's $200-$300 budget)
- 🤖 **Autonomous**: Zero hardcoded responses - all AI-generated

## 🛠️ AWS Services Used

- **Lambda**: Serverless compute for all functions
- **DynamoDB**: Agent profiles, marketplace registry, negotiation history
- **Bedrock**: Claude Haiku/Sonnet for AI, Titan for embeddings
- **S3**: FAISS vector index storage
- **API Gateway**: RESTful endpoints

## 📊 Files Structure

```
├── ChimpBuddy_CoreAgentHandler.py    # Agent profile management
├── ChimpBridge_RegisterAgent.py      # Marketplace discovery  
├── ChimpBuddy_Broker.py              # AI negotiations
├── ChimpBridge_DemoReset.py          # Demo cleanup
├── ChimpBridge_Demo.ipynb            # Jupyter demo notebook
└── README.md                         # This file
```

## 🎮 Running the Demo

1. **Setup AWS Resources**: Deploy Lambda functions, create DynamoDB tables
2. **Run Jupyter Notebook**: `ChimpBridge_Demo.ipynb`
3. **Watch AI Agents**: Register → Discover → Negotiate → Deal!
4. **Reset Demo**: Call reset endpoint between demonstrations

## 🔮 MCP Server Ready

The system is architected for **Model Context Protocol (MCP)** integration:
- ✅ Structured agent profiles and tools
- ✅ Vector search capabilities  
- ✅ Negotiation state management
- ✅ RESTful API endpoints

**Future MCP Servers:**
- Agent Discovery MCP Server
- Negotiation MCP Server  
- Profile Management MCP Server

## 🏆 Hackathon Innovation

**Why This Wins:**
- 🤖 **Pure AI Autonomy**: Agents think and negotiate independently
- 🔍 **Semantic Matching**: Vector similarity finds compatible partners
- 💬 **Natural Conversations**: Claude generates realistic negotiations
- 🏗️ **Production Architecture**: Scalable AWS serverless design
- 🔮 **Future-Ready**: MCP integration for AI ecosystem expansion

## 🎯 Live Demo

**🚀 Interactive Colab Demo**: https://colab.research.google.com/drive/1k7SFK3n79a0T1KQwQV6h-IJMaWykRxr-?usp=sharing

**Reset Environment**: https://6tekwkwbpc.execute-api.us-east-1.amazonaws.com/default/ChimpBridge_DemoReset

**Demo Flow**:
1. Register AI buyer and seller agents
2. Agents discover each other via semantic search
3. Watch autonomous AI-to-AI negotiation
4. Deal completion with AI reasoning

---

*Built for Hackathon 3.0 - Autonomous AI Agent Marketplace*
