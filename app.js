let currentData = null;

async function loadTransactions() {
    try {
        const response = await fetch('/api/transactions');
        currentData = await response.json();
        updateUI();
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

function updateUI() {
    if (!currentData) return;

    document.getElementById('balance').textContent = `$${currentData.balance.toFixed(2)}`;
    document.getElementById('budget').textContent = `$${currentData.budget.toFixed(2)}`;
    
    const pet = document.getElementById('pet');
    pet.className = `pet ${currentData.pet.mood}`;
    document.getElementById('pet-message').textContent = currentData.pet.message;
    
    const transactionsList = document.getElementById('transactions-list');
    
    if (currentData.transactions.length === 0) {
        transactionsList.innerHTML = '<p class="empty-state">No transactions yet. Add one to get started!</p>';
    } else {
        transactionsList.innerHTML = currentData.transactions
            .slice()
            .reverse()
            .map(trans => `
                <div class="transaction-item">
                    <div class="transaction-info">
                        <div class="transaction-category">${trans.category}</div>
                        <div class="transaction-description">${trans.description}</div>
                        <div class="transaction-date">${trans.date}</div>
                    </div>
                    <div class="transaction-amount ${trans.type}">
                        ${trans.type === 'expense' ? '-' : '+'}$${trans.amount.toFixed(2)}
                    </div>
                </div>
            `).join('');
    }
}

document.getElementById('transaction-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const type = formData.get('type');
    const amount = document.getElementById('amount').value;
    const category = document.getElementById('category').value;
    const description = document.getElementById('description').value;
    
    try {
        const response = await fetch('/api/transactions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                type,
                amount: parseFloat(amount),
                category,
                description
            })
        });
        
        currentData = await response.json();
        updateUI();
        e.target.reset();
    } catch (error) {
        console.error('Error adding transaction:', error);
        alert('Failed to add transaction. Please try again.');
    }
});

document.getElementById('budget-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const newBudget = document.getElementById('new-budget').value;
    
    try {
        const response = await fetch('/api/budget', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                budget: parseFloat(newBudget)
            })
        });
        
        currentData = await response.json();
        updateUI();
        e.target.reset();
    } catch (error) {
        console.error('Error updating budget:', error);
        alert('Failed to update budget. Please try again.');
    }
});

document.getElementById('reset-btn').addEventListener('click', async () => {
    if (confirm('Are you sure you want to reset all data? This cannot be undone.')) {
        try {
            await fetch('/api/reset', {
                method: 'POST'
            });
            
            await loadTransactions();
        } catch (error) {
            console.error('Error resetting data:', error);
            alert('Failed to reset data. Please try again.');
        }
    }
});

loadTransactions();
