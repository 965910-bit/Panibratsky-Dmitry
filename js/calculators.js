// Calculators page functionality

class CalculatorsManager {
    constructor() {
        this.calculators = [];
        this.initialize();
    }

    async initialize() {
        await this.loadData();
        this.renderCalculators();
    }

    async loadData() {
        try {
            const data = await fetch('/data/calculators.json');
            if (!data.ok) throw new Error('Failed to load calculators data');
            
            const jsonData = await data.json();
            this.calculators = jsonData.calculators || [];
            
        } catch (error) {
            console.error('Error loading calculators:', error);
            this.showError('Ошибка загрузки данных калькуляторов');
        }
    }

    renderCalculators() {
        const container = document.getElementById('calculators-container');
        if (!container) return;

        if (this.calculators.length === 0) {
            container.innerHTML = `
                <div class="error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Калькуляторы не найдены</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.calculators.map(calc => `
            <div class="calculator-card" id="${calc.id}">
                <div class="calculator-icon">
                    ${calc.icon}
                </div>
                <h3>${calc.title}</h3>
                <p class="calculator-description">${calc.description}</p>
                
                <div class="calculator-form">
                    ${calc.fields.map(field => `
                        <div class="form-group">
                            <label for="${calc.id}-${field.name}">${field.label}</label>
                            <input 
                                type="${field.type}" 
                                id="${calc.id}-${field.name}" 
                                placeholder="${field.placeholder || ''}"
                                ${field.required ? 'required' : ''}
                            >
                        </div>
                    `).join('')}
                </div>
                
                <button class="calculate-btn" onclick="calculatorsManager.calculate('${calc.id}')">
                    <i class="fas fa-calculator"></i>
                    Рассчитать
                </button>
                
                <div class="calculator-result" id="${calc.id}-result">
                    <!-- Results will be inserted here -->
                </div>
            </div>
        `).join('');
    }

    calculate(calculatorId) {
        const calculator = this.calculators.find(calc => calc.id === calculatorId);
        if (!calculator) return;

        // Get input values
        const inputs = {};
        let valid = true;

        calculator.fields.forEach(field => {
            const input = document.getElementById(`${calculatorId}-${field.name}`);
            let value = input.value.trim();

            // Validation
            if (field.required && !value) {
                valid = false;
                input.style.borderColor = '#e74c3c';
            } else {
                input.style.borderColor = '';
                // Convert to number if needed
                inputs[field.name] = field.type === 'number' ? parseFloat(value) : value;
            }
        });

        if (!valid) {
            alert('Пожалуйста, заполните все обязательные поля');
            return;
        }

        // Perform calculation
        const result = this.performCalculation(calculatorId, inputs);
        this.displayResult(calculatorId, result);
    }

    performCalculation(calculatorId, inputs) {
        switch (calculatorId) {
            case 'npv':
                return this.calculateNPV(inputs);
            case 'roi':
                return this.calculateROI(inputs);
            case 'inventory-turnover':
                return this.calculateInventoryTurnover(inputs);
            case 'service-level':
                return this.calculateServiceLevel(inputs);
            case 'tco':
                return this.calculateTCO(inputs);
            case 'staff-turnover':
                return this.calculateStaffTurnover(inputs);
            default:
                return { error: 'Неизвестный калькулятор' };
        }
    }

    calculateNPV(inputs) {
        const { initialInvestment, cashFlows, discountRate } = inputs;
        let npv = -initialInvestment;
        
        // Parse cash flows (comma separated)
        const flows = cashFlows.split(',').map(val => parseFloat(val.trim()));
        
        flows.forEach((cashFlow, year) => {
            npv += cashFlow / Math.pow(1 + discountRate/100, year + 1);
        });

        return {
            npv: npv.toFixed(2) + ' руб.',
            interpretation: npv >= 0 ? '✅ Проект прибыльный' : '❌ Проект убыточный'
        };
    }

    calculateROI(inputs) {
        const { investment, gain } = inputs;
        const roi = ((gain - investment) / investment) * 100;
        
        return {
            roi: roi.toFixed(2) + '%',
            interpretation: roi >= 0 ? '✅ Инвестиция окупается' : '❌ Инвестиция не окупается'
        };
    }

    calculateInventoryTurnover(inputs) {
        const { cogs, averageInventory } = inputs;
        const turnover = cogs / averageInventory;
        
        let interpretation = '';
        if (turnover < 2) interpretation = '⚠️ Низкая оборачиваемость';
        else if (turnover < 6) interpretation = '✅ Средняя оборачиваемость';
        else interpretation = '🚀 Высокая оборачиваемость';
        
        return {
            turnover: turnover.toFixed(2),
            interpretation: interpretation
        };
    }

    calculateServiceLevel(inputs) {
        const { ordersFulfilled, totalOrders } = inputs;
        const serviceLevel = (ordersFulfilled / totalOrders) * 100;
        
        let interpretation = '';
        if (serviceLevel >= 95) interpretation = '🚀 Отличный уровень сервиса';
        else if (serviceLevel >= 90) interpretation = '✅ Хороший уровень сервиса';
        else interpretation = '⚠️ Требуются улучшения';
        
        return {
            serviceLevel: serviceLevel.toFixed(2) + '%',
            interpretation: interpretation
        };
    }

    calculateTCO(inputs) {
        const { purchasePrice, maintenance, operations, downtime } = inputs;
        const tco = purchasePrice + maintenance + operations + downtime;
        
        return {
            tco: tco.toFixed(2) + ' руб.',
            interpretation: '💰 Общая стоимость владения рассчитана'
        };
    }

    calculateStaffTurnover(inputs) {
        const { employeesLeft, averageEmployees } = inputs;
        const turnoverRate = (employeesLeft / averageEmployees) * 100;
        
        let interpretation = '';
        if (turnoverRate < 10) interpretation = '✅ Низкая текучесть';
        else if (turnoverRate < 20) interpretation = '⚠️ Средняя текучесть';
        else interpretation = '❌ Высокая текучесть';
        
        return {
            turnoverRate: turnoverRate.toFixed(2) + '%',
            interpretation: interpretation
        };
    }

    displayResult(calculatorId, result) {
        const resultElement = document.getElementById(`${calculatorId}-result`);
        if (!resultElement) return;

        if (result.error) {
            resultElement.innerHTML = `
                <div style="color: #e74c3c;">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>${result.error}</p>
                </div>
            `;
        } else {
            resultElement.innerHTML = `
                <h4>Результат:</h4>
                ${Object.entries(result).map(([key, value]) => `
                    <div class="result-item">
                        <strong>${this.getResultLabel(key)}:</strong>
                        <span class="result-value">${value}</span>
                    </div>
                `).join('')}
            `;
        }

        resultElement.style.display = 'block';
    }

    getResultLabel(key) {
        const labels = {
            npv: 'Чистая приведенная стоимость (NPV)',
            roi: 'Возврат инвестиций (ROI)',
            turnover: 'Оборачиваемость запасов',
            serviceLevel: 'Уровень обслуживания',
            tco: 'Общая стоимость владения (TCO)',
            turnoverRate: 'Коэффициент текучести',
            interpretation: 'Интерпретация'
        };
        return labels[key] || key;
    }

    showError(message) {
        const container = document.getElementById('calculators-container');
        if (container) {
            container.innerHTML = `
                <div class="error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>${message}</p>
                </div>
            `;
        }
    }
}

// Initialize when DOM is loaded
let calculatorsManager;
document.addEventListener('DOMContentLoaded', () => {
    calculatorsManager = new CalculatorsManager();
});
