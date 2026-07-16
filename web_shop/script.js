// 3D Card Hover Effect on Hero visual
const mainCard = document.getElementById('mainCard');
if (mainCard) {
    mainCard.addEventListener('mousemove', (e) => {
        const rect = mainCard.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        const rotateX = -(y - centerY) / 10;
        const rotateY = (x - centerX) / 10;
        
        mainCard.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
    });
    
    mainCard.addEventListener('mouseleave', () => {
        mainCard.style.transform = 'rotateX(0) rotateY(0) scale(1)';
    });
}

// Global Checkout Variables
let currentPlan = 'Monthly';
let currentPrice = 15;

// Open Checkout Section on Package Click
function openCheckout(planName, price) {
    currentPlan = planName;
    currentPrice = price;
    
    document.getElementById('selectedPlanName').textContent = planName === 'Monthly' ? 'الاشتراك الشهري' : 'اشتراك مدى الحياة';
    document.getElementById('selectedPlanPrice').textContent = `$${price}`;
    
    const checkoutSec = document.getElementById('checkout');
    checkoutSec.classList.remove('hidden');
    
    // Smooth scroll to checkout
    checkoutSec.scrollIntoView({ behavior: 'smooth' });
}

// 3D Credit Card Rotation & Focus Handlers
const creditCard = document.getElementById('creditCard');

function flipCreditCard(isBack) {
    if (isBack) {
        creditCard.classList.add('flipped');
    } else {
        creditCard.classList.remove('flipped');
    }
}

// Format Input - Card Number (Adds space every 4 digits)
function formatCardNumber(input) {
    let value = input.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    let formatted = '';
    for (let i = 0; i < value.length; i++) {
        if (i > 0 && i % 4 === 0) {
            formatted += ' ';
        }
        formatted += value[i];
    }
    input.value = formatted;
    
    // Update preview card
    const displayNum = document.getElementById('displayCardNumber');
    displayNum.textContent = formatted || '•••• •••• •••• ••••';
}

// Format Input - Expiry Date (Adds slash MM/YY)
function formatExpiry(input) {
    let value = input.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
    if (value.length > 2) {
        input.value = value.substring(0, 2) + '/' + value.substring(2, 4);
    } else {
        input.value = value;
    }
    
    // Update preview card
    document.getElementById('displayExpiry').textContent = input.value || 'MM/YY';
}

// Update Cardholder Name & CVV in preview
document.getElementById('cardName').addEventListener('input', (e) => {
    document.getElementById('displayName').textContent = e.target.value.toUpperCase() || 'YOUR NAME';
});

document.getElementById('cardCvv').addEventListener('input', (e) => {
    document.getElementById('displayCvv').textContent = e.target.value || '***';
});

// Process Simulated Premium Payment & Generate Database Locked Keys
function generateLicenseKey(tier) {
    const prefix = tier === 'Lifetime' ? 'LFT' : 'MON';
    const hex = '0123456789ABCDEF';
    let parts = [];
    for (let i = 0; i < 4; i++) {
        let part = '';
        for (let j = 0; j < 4; j++) {
            part += hex[Math.floor(Math.random() * 16)];
        }
        parts.push(part);
    }
    return `${prefix}-${parts.join('-')}`;
}

function processPayment(event) {
    event.preventDefault();
    
    const payButton = document.getElementById('payButton');
    payButton.disabled = true;
    payButton.textContent = 'جاري معالجة المعاملة الآمنة... ⏳';
    
    setTimeout(() => {
        // Successful simulation! Generate locked license key
        const newKey = generateLicenseKey(currentPlan);
        const deviceId = document.getElementById('deviceId').value.trim();
        
        // Show success modal
        document.getElementById('generatedKeyDisplay').textContent = newKey;
        document.getElementById('successModal').classList.remove('hidden');
        
        // Reset button
        payButton.disabled = false;
        payButton.textContent = 'تأكيد الدفع والتفعيل الفوري 🔒';
    }, 2500);
}

// Clipboard Copy logic for license key
function copyLicenseKey() {
    const key = document.getElementById('generatedKeyDisplay').textContent;
    navigator.clipboard.writeText(key).then(() => {
        alert('تم نسخ مفتاح التفعيل بنجاح! 📋');
    });
}

function closeSuccessModal() {
    document.getElementById('successModal').classList.add('hidden');
    document.getElementById('paymentForm').reset();
    document.getElementById('displayCardNumber').textContent = '•••• •••• •••• ••••';
    document.getElementById('displayName').textContent = 'YOUR NAME';
    document.getElementById('displayExpiry').textContent = 'MM/YY';
    document.getElementById('displayCvv').textContent = '***';
    document.getElementById('checkout').classList.add('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
