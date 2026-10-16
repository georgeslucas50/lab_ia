// Arquivo JavaScript principal para controle da apresentação
let currentSlideIndex = 0;
const totalSlides = 11; // O número total de slides no HTML

document.addEventListener("DOMContentLoaded", () => {
    console.log("Apresentação inicializada.");
    
    // Força o loop do vídeo via JavaScript caso o atributo HTML falhe
    const bgVideo = document.getElementById('bg-video');
    if (bgVideo) {
        bgVideo.addEventListener('ended', () => {
            bgVideo.currentTime = 0;
            bgVideo.play();
        });
    }
    updateButtons();
});

// Função chamada pelo botão "Começar" / "Próximo"
function nextSlide() {
    // 1. Esconde o slide atual
    const currentSlide = document.getElementById(`slide-${currentSlideIndex}`);
    if (currentSlide) {
        currentSlide.classList.remove('active');
    }
    
    // 2. Incrementa o índice do slide
    currentSlideIndex++;
    
    // 3. Se passar do último slide, volta para o início (loop)
    if (currentSlideIndex >= totalSlides) {
        currentSlideIndex = 0;
    }
    
    // 4. Mostra o novo slide adicionando a classe active
    const nextSlideElement = document.getElementById(`slide-${currentSlideIndex}`);
    if (nextSlideElement) {
        nextSlideElement.classList.add('active');
    }

    // 5. Atualiza a exibição e textos dos botões
    updateButtons();
}

// Função para voltar ao slide anterior
function prevSlide() {
    if (currentSlideIndex > 0) {
        // 1. Esconde o slide atual
        const currentSlide = document.getElementById(`slide-${currentSlideIndex}`);
        if (currentSlide) {
            currentSlide.classList.remove('active');
        }
        
        // 2. Decrementa o índice
        currentSlideIndex--;
        
        // 3. Mostra o slide anterior
        const prevSlideElement = document.getElementById(`slide-${currentSlideIndex}`);
        if (prevSlideElement) {
            prevSlideElement.classList.add('active');
        }
        
        // 4. Atualiza os botões
        updateButtons();
    }
}

// Controla a visibilidade dos botões e o comportamento do vídeo/imagem
function updateButtons() {
    const nextBtn = document.getElementById('next-slide-btn');
    const prevBtn = document.getElementById('prev-slide-btn');
    const bgVideo = document.getElementById('bg-video');
    const bgImage = document.getElementById('bg-image');
    
    // Slide inicial: Mostra vídeo, oculta imagem
    if (currentSlideIndex === 0) {
        nextBtn.innerHTML = 'Começar <span>&#8594;</span>';
        if (bgVideo) {
            bgVideo.play();
            bgVideo.style.opacity = '0.15';
        }
        if (bgImage) bgImage.style.opacity = '0';
    } else {
        // Slides de conteúdo: Oculta/pausa vídeo, mostra imagem
        if (currentSlideIndex === totalSlides - 1) {
            nextBtn.innerHTML = 'Reiniciar <span>&#10226;</span>';
        } else {
            nextBtn.innerHTML = 'Próximo <span>&#8594;</span>';
        }
        
        if (bgVideo) {
            bgVideo.style.opacity = '0';
            // Pausa o vídeo após a transição de CSS finalizar (0.8s) para manter a fluidez
            setTimeout(() => bgVideo.pause(), 800); 
        }
        if (bgImage) {
            bgImage.style.opacity = '0.2'; // Opacidade controlada para leitura perfeita
        }
    }
    
    // Esconde o botão voltar no primeiro slide
    if (currentSlideIndex === 0) {
        prevBtn.style.display = 'none';
    } else {
        prevBtn.style.display = 'flex';
    }
}
