"""
DYNAX ERC20 Token Template
มาตรฐาน token สำหรับ DYNAX DVM
"""

ERC20_CODE = """
contract DYXToken {
    // Token metadata
    string name = "DYNAX Token"
    string symbol = "DYX"
    uint8 decimals = 18
    uint256 totalSupply = 1000000
    
    // Balances
    mapping balances
    
    // Allowances
    mapping allowances
    
    // Constructor
    function init() {
        balances[caller] = totalSupply
    }
    
    // Get balance
    function balanceOf(account) {
        return balances[account]
    }
    
    // Transfer tokens
    function transfer(to, amount) {
        if balances[caller] < amount {
            return {"status": "error", "message": "Insufficient balance"}
        }
        balances[caller] = balances[caller] - amount
        balances[to] = balances[to] + amount
        emit("Transfer", {"from": caller, "to": to, "amount": amount})
        return {"status": "success", "balance": balances[caller]}
    }
    
    // Approve spending
    function approve(spender, amount) {
        allowances[caller][spender] = amount
        emit("Approval", {"owner": caller, "spender": spender, "amount": amount})
        return {"status": "success"}
    }
    
    // Transfer from approved account
    function transferFrom(from, to, amount) {
        if allowances[from][caller] < amount {
            return {"status": "error", "message": "Allowance exceeded"}
        }
        if balances[from] < amount {
            return {"status": "error", "message": "Insufficient balance"}
        }
        allowances[from][caller] = allowances[from][caller] - amount
        balances[from] = balances[from] - amount
        balances[to] = balances[to] + amount
        emit("Transfer", {"from": from, "to": to, "amount": amount})
        return {"status": "success"}
    }
    
    // Get total supply
    function getTotalSupply() {
        return totalSupply
    }
}
"""

print("✅ ERC20 Template loaded")
print(f"   Name: DYNAX Token")
print(f"   Symbol: DYX")
print(f"   Total Supply: 1,000,000")
