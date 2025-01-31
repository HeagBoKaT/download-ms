async function installApp() {
    const url = document.getElementById('storeUrl').value;
    const resultDiv = document.getElementById('statusMessage');
    const installBtn = document.querySelector('.install-btn');
    
    // Сброс состояния
    resultDiv.className = 'status-message';
    resultDiv.innerHTML = '<div class="loading"><div class="loading-spinner"></div>Обработка запроса...</div>';
    installBtn.disabled = true;
    
    try {
        const response = await eel.process_store_link(url)();
        
        if(response.startsWith('Ошибка')) {
            resultDiv.innerHTML = `<div class="error">${response}</div>`;
        } else {
            resultDiv.innerHTML = `
                <div class="success">
                    <i class="fas fa-check-circle"></i>
                    ${response}
                </div>
            `;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="error">Произошла ошибка: ${error.message}</div>`;
    } finally {
        installBtn.disabled = false;
    }
}

// Добавим анимацию статусных сообщений
function showStatus(message, type = 'info') {
    const statusElem = document.getElementById('statusMessage');
    statusElem.className = `status-message ${type}-message`;
    statusElem.innerHTML = `
        <i class="fas fa-${type === 'error' ? 'times-circle' : 'check-circle'}"></i>
        ${message}
    `;
    statusElem.style.display = 'block';
} 