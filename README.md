# Tribo Slot Game Bot with Web3 Payments

A Telegram bot for a slot game with automatic blockchain payments via smart contracts.

## Features

- Slot game with multiple prize tiers
- Automatic Web3 payments when users claim prizes
- Wallet registration system
- Cooldown management for winners and losers
- Global statistics tracking
- Admin notifications

## Setup

### 1. Install Dependencies

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 2. Environment Variables

Create a `.env` file or set the following environment variables:

\`\`\`bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Web3 Configuration
RPC_URL=https://your-rpc-url
PRIVATE_KEY=your_private_key_for_bot_wallet
CONTRACT_ADDRESS=0xYourContractAddress
CHAIN_ID=4801
\`\`\`

### 3. Smart Contract

The bot expects a smart contract with the following functions:

```solidity
function claim(address tokenAddress, uint256 amount, address to) external;
function getBalance(address tokenAddress) external view returns (uint256);
