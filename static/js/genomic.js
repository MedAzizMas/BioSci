// Genomic Analysis Page JavaScript
document.addEventListener('DOMContentLoaded', () => {
    const searchForm = document.getElementById('searchForm');
    const questionInput = document.getElementById('questionInput');
    const topKSlider = document.getElementById('topK');
    const topKValue = document.getElementById('topKValue');
    const resultsArea = document.getElementById('resultsArea');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const answerSection = document.getElementById('answerSection');
    const answerContent = document.getElementById('answerContent');
    const graphSection = document.getElementById('graphSection');
    const graphContainer = document.getElementById('graphContainer');
    const sourcesSection = document.getElementById('sourcesSection');
    const sourcesContainer = document.getElementById('sourcesContainer');

    // Typing animation state
    let typingInterval = null;
    let isTyping = false;

    // ==========================================
    // ANIMATED STATS COUNTER
    // ==========================================
    function animateCounters() {
        const counters = document.querySelectorAll('.counter');
        
        counters.forEach(counter => {
            const target = parseInt(counter.dataset.target.replace(/,/g, ''), 10);
            if (isNaN(target)) return;
            
            const duration = 2000; // 2 seconds
            const startTime = performance.now();
            const startValue = 0;
            
            function easeOutQuart(t) {
                return 1 - Math.pow(1 - t, 4);
            }
            
            function updateCounter(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const easedProgress = easeOutQuart(progress);
                const currentValue = Math.floor(startValue + (target - startValue) * easedProgress);
                
                counter.textContent = currentValue.toLocaleString();
                
                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = target.toLocaleString();
                }
            }
            
            requestAnimationFrame(updateCounter);
        });
    }
    
    // Start counter animation on page load
    animateCounters();

    // Autocomplete state
    let autocompleteTimeout = null;
    const autocompleteDropdown = document.getElementById('autocompleteDropdown');

    // Store last query for graph refresh on theme change
    let lastQuery = null;
    let lastTopK = 10;

    // Voice Input Setup
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceStatus = document.getElementById('voiceStatus');
    const voiceStatusText = document.getElementById('voiceStatusText');
    
    let recognition = null;
    let isListening = false;

    // Check for Web Speech API support
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isListening = true;
            voiceBtn.classList.add('listening');
            voiceStatus.style.display = 'flex';
            voiceStatusText.textContent = 'Listening...';
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            // Show interim results in input
            if (interimTranscript) {
                questionInput.value = interimTranscript;
                voiceStatusText.textContent = 'Hearing: ' + interimTranscript;
            }

            // Set final result
            if (finalTranscript) {
                questionInput.value = finalTranscript;
                voiceStatusText.textContent = 'Got it!';
            }
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            voiceStatusText.textContent = 'Error: ' + event.error;
            setTimeout(() => {
                stopListening();
            }, 1500);
        };

        recognition.onend = () => {
            stopListening();
        };

        // Voice button click handler
        voiceBtn.addEventListener('click', () => {
            if (isListening) {
                recognition.stop();
            } else {
                questionInput.value = '';
                recognition.start();
            }
        });
    } else {
        // Browser doesn't support speech recognition
        voiceBtn.classList.add('not-supported');
        voiceBtn.title = 'Voice input not supported in this browser';
    }

    function stopListening() {
        isListening = false;
        voiceBtn.classList.remove('listening');
        setTimeout(() => {
            voiceStatus.style.display = 'none';
        }, 1000);
    }

    // ==========================================
    // TEXT-TO-SPEECH (Read Answer Aloud)
    // ==========================================
    const speakBtn = document.getElementById('speakBtn');
    let speechSynthesis = window.speechSynthesis;
    let currentUtterance = null;
    let isSpeaking = false;

    if (speakBtn && speechSynthesis) {
        speakBtn.addEventListener('click', () => {
            if (isSpeaking) {
                // Stop speaking
                speechSynthesis.cancel();
                stopSpeaking();
            } else {
                // Start speaking
                const text = answerContent.textContent || answerContent.innerText;
                if (!text.trim()) return;
                
                currentUtterance = new SpeechSynthesisUtterance(text);
                currentUtterance.rate = 1.0;
                currentUtterance.pitch = 1.0;
                currentUtterance.volume = 1.0;
                
                // Try to use a good English voice
                const voices = speechSynthesis.getVoices();
                const englishVoice = voices.find(v => v.lang.startsWith('en') && v.name.includes('Google')) 
                    || voices.find(v => v.lang.startsWith('en'));
                if (englishVoice) {
                    currentUtterance.voice = englishVoice;
                }
                
                currentUtterance.onstart = () => {
                    isSpeaking = true;
                    speakBtn.classList.add('speaking');
                    speakBtn.querySelector('span').textContent = 'Stop';
                    speakBtn.querySelector('i').className = 'fas fa-stop';
                };
                
                currentUtterance.onend = () => {
                    stopSpeaking();
                };
                
                currentUtterance.onerror = () => {
                    stopSpeaking();
                };
                
                speechSynthesis.speak(currentUtterance);
            }
        });
    }

    function stopSpeaking() {
        isSpeaking = false;
        if (speakBtn) {
            speakBtn.classList.remove('speaking');
            speakBtn.querySelector('span').textContent = 'Listen';
            speakBtn.querySelector('i').className = 'fas fa-volume-up';
        }
    }

    // ==========================================
    // TRANSLATE TO FRENCH
    // ==========================================
    const translateBtn = document.getElementById('translateBtn');
    let originalAnswer = '';
    let translatedAnswer = '';
    let isShowingTranslation = false;

    if (translateBtn) {
        translateBtn.addEventListener('click', async () => {
            // If already showing translation, toggle back to English
            if (isShowingTranslation) {
                answerContent.textContent = originalAnswer;
                translateBtn.classList.remove('translated');
                translateBtn.querySelector('span').textContent = '🇫🇷 French';
                isShowingTranslation = false;
                return;
            }

            // If we already have a translation, just show it
            if (translatedAnswer) {
                answerContent.textContent = translatedAnswer;
                translateBtn.classList.add('translated');
                translateBtn.querySelector('span').textContent = '🇬🇧 English';
                isShowingTranslation = true;
                return;
            }

            // Get current answer text
            const text = answerContent.textContent || answerContent.innerText;
            if (!text.trim()) return;

            // Store original
            originalAnswer = text;

            // Show loading state
            translateBtn.classList.add('translating');
            translateBtn.querySelector('span').textContent = 'Translating...';

            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text, target_lang: 'french' })
                });

                const data = await response.json();

                if (data.success && data.translated) {
                    translatedAnswer = data.translated;
                    answerContent.textContent = translatedAnswer;
                    translateBtn.classList.remove('translating');
                    translateBtn.classList.add('translated');
                    translateBtn.querySelector('span').textContent = '🇬🇧 English';
                    isShowingTranslation = true;
                } else {
                    throw new Error(data.error || 'Translation failed');
                }
            } catch (error) {
                console.error('Translation error:', error);
                translateBtn.classList.remove('translating');
                translateBtn.querySelector('span').textContent = '🇫🇷 French';
                alert('Translation failed. Please try again.');
            }
        });
    }

    // Update slider value display
    topKSlider.addEventListener('input', () => {
        topKValue.textContent = topKSlider.value;
    });

    // Example question buttons
    document.querySelectorAll('.example-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            questionInput.value = btn.dataset.question;
            questionInput.focus();
        });
    });

    // Loading messages that cycle
    const loadingMessages = [
        'Thinking...',
        'Searching knowledge graph...',
        'Analyzing relationships...',
        'Finding connections...',
        'Almost there...'
    ];
    let loadingMsgIndex = 0;
    let loadingMsgInterval = null;

    function startLoadingMessages() {
        const loadingText = document.getElementById('loadingText');
        loadingMsgIndex = 0;
        loadingText.textContent = loadingMessages[0];
        
        loadingMsgInterval = setInterval(() => {
            loadingMsgIndex = (loadingMsgIndex + 1) % loadingMessages.length;
            loadingText.textContent = loadingMessages[loadingMsgIndex];
        }, 2000);
    }

    function stopLoadingMessages() {
        if (loadingMsgInterval) {
            clearInterval(loadingMsgInterval);
            loadingMsgInterval = null;
        }
    }

    // Get current theme
    function getCurrentTheme() {
        const theme = document.documentElement.getAttribute('data-theme') || 'light';
        console.log('Current theme:', theme);
        return theme;
    }

    // Refresh graph with new theme
    async function refreshGraphTheme() {
        if (!lastQuery || graphSection.style.display === 'none') return;
        
        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: lastQuery,
                    top_k: lastTopK,
                    theme: getCurrentTheme()
                })
            });
            const data = await response.json();
            if (data.graph_html) {
                graphContainer.innerHTML = `<iframe srcdoc="${escapeHtml(data.graph_html)}"></iframe>`;
            }
        } catch (error) {
            console.error('Failed to refresh graph theme:', error);
        }
    }

    // Listen for theme changes
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            // Wait a bit for theme to change, then refresh graph
            setTimeout(refreshGraphTheme, 100);
        });
    }

    // Store entities for highlighting
    let currentEntities = null;

    // Form submission
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = questionInput.value.trim();
        if (!question) return;

        // Store for potential graph refresh
        lastQuery = question;
        lastTopK = parseInt(topKSlider.value);

        // Reset translation state for new query
        originalAnswer = '';
        translatedAnswer = '';
        isShowingTranslation = false;
        if (translateBtn) {
            translateBtn.classList.remove('translated', 'translating');
            translateBtn.querySelector('span').textContent = '🇫🇷 French';
        }

        // Show loading
        resultsArea.style.display = 'block';
        loadingIndicator.style.display = 'flex';
        answerSection.style.display = 'none';
        graphSection.style.display = 'none';
        sourcesSection.style.display = 'none';
        startLoadingMessages();

        try {
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: question,
                    top_k: parseInt(topKSlider.value),
                    theme: getCurrentTheme()
                })
            });

            const data = await response.json();
            stopLoadingMessages();
            loadingIndicator.style.display = 'none';

            if (data.error) {
                answerContent.textContent = 'Error: ' + data.error;
                answerSection.style.display = 'block';
                return;
            }

            // Store entities for highlighting
            currentEntities = data.entities;

            // Reset animation classes
            answerSection.classList.remove('section-visible');
            graphSection.classList.remove('section-visible');
            sourcesSection.classList.remove('section-visible');
            document.getElementById('followupSection').classList.remove('section-visible');

            // Display answer with typing animation and entity highlighting
            answerSection.style.display = 'block';
            // Trigger reflow then add animation class
            void answerSection.offsetWidth;
            answerSection.classList.add('section-visible');
            // Use simple text display (highlighting disabled for now)
            typeTextSimple(data.answer, answerContent);

            // Display follow-up questions
            if (data.followup_questions && data.followup_questions.length > 0) {
                renderFollowupQuestions(data.followup_questions);
            } else {
                document.getElementById('followupSection').style.display = 'none';
            }

            // Display graph with staggered animation
            if (data.graph_html) {
                graphContainer.innerHTML = `<iframe srcdoc="${escapeHtml(data.graph_html)}"></iframe>`;
                graphSection.style.display = 'block';
                void graphSection.offsetWidth;
                graphSection.classList.add('section-visible');
            }

            // Display sources with staggered animation
            if (data.sources && data.sources.length > 0) {
                renderSources(data.sources);
                sourcesSection.style.display = 'block';
                void sourcesSection.offsetWidth;
                sourcesSection.classList.add('section-visible');
            }

        } catch (error) {
            stopLoadingMessages();
            loadingIndicator.style.display = 'none';
            answerContent.textContent = 'Error connecting to server. Please try again.';
            answerSection.style.display = 'block';
        }
    });

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML.replace(/"/g, '&quot;');
    }

    function renderFollowupQuestions(questions) {
        const followupSection = document.getElementById('followupSection');
        const followupContainer = document.getElementById('followupQuestions');
        
        followupContainer.innerHTML = questions.map(q => `
            <button class="followup-btn" data-question="${escapeHtml(q)}">
                <i class="fas fa-arrow-right"></i>
                <span>${q}</span>
            </button>
        `).join('');
        
        followupSection.style.display = 'block';
        // Trigger animation
        void followupSection.offsetWidth;
        followupSection.classList.add('section-visible');
        
        // Add click handlers to follow-up buttons
        followupContainer.querySelectorAll('.followup-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                questionInput.value = btn.dataset.question;
                questionInput.focus();
                // Optionally auto-submit
                searchForm.dispatchEvent(new Event('submit'));
            });
        });
    }

    function getEntityIcon(type) {
        const icons = {
            'disease_subgraph': '🦠',
            'chemical_subgraph': '💊',
            'gene_subgraph': '🧬',
            'pathway_subgraph': '🔄'
        };
        return icons[type] || '📄';
    }

    function getEntityLabel(type) {
        const labels = {
            'disease_subgraph': 'Disease',
            'chemical_subgraph': 'Chemical/Drug',
            'gene_subgraph': 'Gene',
            'pathway_subgraph': 'Pathway'
        };
        return labels[type] || 'Entity';
    }

    function renderSources(sources) {
        // Group by type
        const byType = {};
        sources.forEach(source => {
            const type = source.type;
            if (!byType[type]) byType[type] = [];
            byType[type].push(source);
        });

        // Create tabs and content
        let tabsHtml = '<div class="source-tabs">';
        let contentHtml = '';

        Object.entries(byType).forEach(([type, items], index) => {
            const icon = getEntityIcon(type);
            const label = getEntityLabel(type);
            const activeClass = index === 0 ? 'active' : '';
            const displayStyle = index === 0 ? '' : 'display: none;';

            tabsHtml += `<button class="source-tab ${activeClass}" data-type="${type}">
                ${icon} ${label}s (${items.length})
            </button>`;

            contentHtml += `<div class="source-group" data-type="${type}" style="${displayStyle}">`;
            items.forEach(item => {
                contentHtml += `
                    <div class="source-item">
                        <div class="source-header">
                            <span class="source-title">
                                ${icon} ${item.center_entity}
                            </span>
                            <span class="source-score">Score: ${item.score.toFixed(3)}</span>
                        </div>
                        <div class="source-content">
                            <pre>${item.text}</pre>
                        </div>
                    </div>
                `;
            });
            contentHtml += '</div>';
        });

        tabsHtml += '</div>';
        sourcesContainer.innerHTML = tabsHtml + contentHtml;

        // Tab click handlers
        sourcesContainer.querySelectorAll('.source-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                sourcesContainer.querySelectorAll('.source-tab').forEach(t => t.classList.remove('active'));
                sourcesContainer.querySelectorAll('.source-group').forEach(g => g.style.display = 'none');
                tab.classList.add('active');
                sourcesContainer.querySelector(`.source-group[data-type="${tab.dataset.type}"]`).style.display = 'block';
            });
        });

        // Expand/collapse source items
        sourcesContainer.querySelectorAll('.source-header').forEach(header => {
            header.addEventListener('click', () => {
                header.parentElement.classList.toggle('expanded');
            });
        });
    }

    // ==========================================
    // TYPING ANIMATION WITH ENTITY HIGHLIGHTING
    // ==========================================
    let fullText = '';
    let fullEntities = null;
    
    // Simple typing animation without highlighting
    function typeTextSimple(text, element, speed = 12) {
        if (typingInterval) {
            clearInterval(typingInterval);
        }
        
        fullText = text;
        isTyping = true;
        element.textContent = '';
        element.classList.add('typing-active');
        
        const words = text.split(/(\s+)/);
        let wordIndex = 0;
        let displayed = '';
        
        typingInterval = setInterval(function() {
            if (wordIndex < words.length) {
                displayed += words[wordIndex];
                element.textContent = displayed;
                wordIndex++;
                element.scrollTop = element.scrollHeight;
            } else {
                clearInterval(typingInterval);
                typingInterval = null;
                isTyping = false;
                element.classList.remove('typing-active');
            }
        }, speed);
    }
    
    function typeTextWithHighlight(text, element, entities, speed = 12) {
        // Stop any existing typing
        if (typingInterval) {
            clearInterval(typingInterval);
        }
        
        fullText = text;
        fullEntities = entities;
        isTyping = true;
        element.innerHTML = '';
        element.classList.add('typing-active');
        
        // Split into words while preserving spaces and newlines
        const words = text.split(/(\s+)/);
        let wordIndex = 0;
        let displayedText = '';
        
        typingInterval = setInterval(() => {
            if (wordIndex < words.length) {
                displayedText += words[wordIndex];
                element.innerHTML = highlightEntities(displayedText, entities);
                wordIndex++;
                
                // Auto-scroll if needed
                element.scrollTop = element.scrollHeight;
            } else {
                // Typing complete
                clearInterval(typingInterval);
                typingInterval = null;
                isTyping = false;
                element.classList.remove('typing-active');
                
                // Add click handlers to highlighted entities
                addEntityClickHandlers(element);
            }
        }, speed);
    }

    // Skip typing animation on click - show full text immediately
    answerContent.addEventListener('click', function(e) {
        if (isTyping && typingInterval) {
            clearInterval(typingInterval);
            typingInterval = null;
            isTyping = false;
            answerContent.textContent = fullText;
            answerContent.classList.remove('typing-active');
        }
    });

    // ==========================================
    // AUTOCOMPLETE
    // ==========================================
    const entityIcons = {
        'disease': '🦠',
        'chemical': '💊',
        'gene': '🧬',
        'pathway': '🔄',
        'entity': '📄'
    };

    questionInput.addEventListener('input', () => {
        const query = questionInput.value.trim();
        
        // Clear previous timeout
        if (autocompleteTimeout) {
            clearTimeout(autocompleteTimeout);
        }
        
        // Hide dropdown if query too short
        if (query.length < 2) {
            hideAutocomplete();
            return;
        }
        
        // Debounce the API call
        autocompleteTimeout = setTimeout(() => {
            fetchSuggestions(query);
        }, 200);
    });

    async function fetchSuggestions(query) {
        try {
            const response = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.suggestions && data.suggestions.length > 0) {
                showAutocomplete(data.suggestions);
            } else {
                hideAutocomplete();
            }
        } catch (error) {
            console.error('Autocomplete error:', error);
            hideAutocomplete();
        }
    }

    function showAutocomplete(suggestions) {
        if (!autocompleteDropdown) return;
        
        autocompleteDropdown.innerHTML = suggestions.map((item, index) => `
            <div class="autocomplete-item ${index === 0 ? 'selected' : ''}" data-name="${item.name}">
                <span class="autocomplete-icon">${entityIcons[item.type] || '📄'}</span>
                <span class="autocomplete-name">${highlightMatch(item.name, questionInput.value)}</span>
                <span class="autocomplete-type">${item.type}</span>
            </div>
        `).join('');
        
        autocompleteDropdown.style.display = 'block';
        
        // Add click handlers
        autocompleteDropdown.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
                selectSuggestion(item.dataset.name);
            });
        });
    }

    function hideAutocomplete() {
        if (autocompleteDropdown) {
            autocompleteDropdown.style.display = 'none';
        }
    }

    function highlightMatch(text, query) {
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        return text.replace(regex, '<strong>$1</strong>');
    }

    function escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function selectSuggestion(name) {
        // Insert entity name into question
        const currentValue = questionInput.value;
        const words = currentValue.split(' ');
        
        // Replace the last word (partial match) with the selected entity
        if (words.length > 0) {
            words[words.length - 1] = name;
            questionInput.value = words.join(' ') + ' ';
        } else {
            questionInput.value = name + ' ';
        }
        
        hideAutocomplete();
        questionInput.focus();
    }

    // Keyboard navigation for autocomplete
    questionInput.addEventListener('keydown', (e) => {
        if (!autocompleteDropdown || autocompleteDropdown.style.display === 'none') return;
        
        const items = autocompleteDropdown.querySelectorAll('.autocomplete-item');
        const selected = autocompleteDropdown.querySelector('.autocomplete-item.selected');
        let selectedIndex = Array.from(items).indexOf(selected);
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                updateSelection(items, selectedIndex);
                break;
            case 'ArrowUp':
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                updateSelection(items, selectedIndex);
                break;
            case 'Enter':
                if (selected) {
                    e.preventDefault();
                    selectSuggestion(selected.dataset.name);
                }
                break;
            case 'Escape':
                hideAutocomplete();
                break;
        }
    });

    function updateSelection(items, index) {
        items.forEach((item, i) => {
            item.classList.toggle('selected', i === index);
        });
    }

    // Hide autocomplete when clicking outside
    document.addEventListener('click', (e) => {
        if (!questionInput.contains(e.target) && !autocompleteDropdown?.contains(e.target)) {
            hideAutocomplete();
        }
    });
});
