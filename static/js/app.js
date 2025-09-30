// PDF OCR 웹 애플리케이션 JavaScript

class PDFAnalyzer {
    constructor() {
        this.socket = null;
        this.currentResults = null;
        this.initializeApp();
    }

    initializeApp() {
        // Socket.IO 초기화
        this.initializeSocket();
        
        // 이벤트 리스너 등록
        this.initializeEventListeners();
        
        // 페이지 로드 완료 알림
        console.log('🚀 PDF OCR 웹 애플리케이션이 시작되었습니다.');
    }

    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('✅ 서버에 연결되었습니다.');
        });

        this.socket.on('disconnect', () => {
            console.log('❌ 서버 연결이 끊어졌습니다.');
        });

        this.socket.on('status', (data) => {
            this.showNotification(data.message, data.type || 'info');
        });

        this.socket.on('chat_response', (data) => {
            this.handleChatResponse(data);
        });
    }

    initializeEventListeners() {
        // 개별 분석 폼
        const individualForm = document.getElementById('individualForm');
        if (individualForm) {
            individualForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleIndividualAnalysis();
            });
        }

        // 채팅창 크기 조절 기능
        this.initializeChatResize();

        // 비교 분석 폼
        const compareForm = document.getElementById('compareForm');
        if (compareForm) {
            compareForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleCompareAnalysis();
            });
        }

        // 채팅 메시지 전송
        const sendChatBtn = document.getElementById('sendChatBtn');
        const chatInput = document.getElementById('chatInput');
        
        if (sendChatBtn) {
            sendChatBtn.addEventListener('click', () => {
                this.sendChatMessage();
            });
        }

        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendChatMessage();
                }
            });
        }

        // 파일 업로드 이벤트
        this.initializeFileUpload();
    }

    initializeFileUpload() {
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                this.validateFile(e.target);
            });
        });
    }

    validateFile(input) {
        const file = input.files[0];
        if (!file) return;

        if (file.type !== 'application/pdf') {
            this.showNotification('PDF 파일만 업로드 가능합니다.', 'error');
            input.value = '';
            return false;
        }

        if (file.size > 50 * 1024 * 1024) { // 50MB
            this.showNotification('파일 크기는 50MB를 초과할 수 없습니다.', 'error');
            input.value = '';
            return false;
        }

        return true;
    }

    async handleIndividualAnalysis() {
        try {
            this.showLoading('개별 상품 분석을 시작합니다...');

            const productName = document.getElementById('individual_product_name').value.trim();
            const urlTab = document.getElementById('individual-url-tab');
            const isUrlActive = urlTab.classList.contains('active');

            let source = '';
            let sourceType = '';

            if (isUrlActive) {
                source = document.getElementById('individual_url').value.trim();
                sourceType = 'url';
                
                if (!source) {
                    throw new Error('PDF URL을 입력해주세요.');
                }
            } else {
                const fileInput = document.getElementById('individual_file');
                if (!fileInput.files.length) {
                    throw new Error('PDF 파일을 선택해주세요.');
                }

                // 파일 업로드
                source = await this.uploadFile(fileInput.files[0]);
                sourceType = 'file';
            }

            // 분석 요청
            const response = await fetch('/api/analyze/individual', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    source: source,
                    source_type: sourceType,
                    product_name: productName
                })
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error);
            }

            this.currentResults = result;
            this.displayResults(result, 'individual');
            this.showNotification('분석이 완료되었습니다!', 'success');

        } catch (error) {
            console.error('개별 분석 오류:', error);
            this.showNotification(error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async handleCompareAnalysis() {
        try {
            this.showLoading('2개 상품 비교 분석을 시작합니다...');

            const product1Name = document.getElementById('product1_name').value.trim();
            const product2Name = document.getElementById('product2_name').value.trim();

            // 첫 번째 상품 소스
            const product1UrlTab = document.getElementById('product1-url-tab');
            const isProduct1UrlActive = product1UrlTab.classList.contains('active');
            
            let source1 = '';
            let source1Type = '';

            if (isProduct1UrlActive) {
                source1 = document.getElementById('product1_url').value.trim();
                source1Type = 'url';
                if (!source1) throw new Error('첫 번째 상품의 PDF URL을 입력해주세요.');
            } else {
                const fileInput = document.getElementById('product1_file');
                if (!fileInput.files.length) throw new Error('첫 번째 상품의 PDF 파일을 선택해주세요.');
                source1 = await this.uploadFile(fileInput.files[0]);
                source1Type = 'file';
            }

            // 두 번째 상품 소스
            const product2UrlTab = document.getElementById('product2-url-tab');
            const isProduct2UrlActive = product2UrlTab.classList.contains('active');
            
            let source2 = '';
            let source2Type = '';

            if (isProduct2UrlActive) {
                source2 = document.getElementById('product2_url').value.trim();
                source2Type = 'url';
                if (!source2) throw new Error('두 번째 상품의 PDF URL을 입력해주세요.');
            } else {
                const fileInput = document.getElementById('product2_file');
                if (!fileInput.files.length) throw new Error('두 번째 상품의 PDF 파일을 선택해주세요.');
                source2 = await this.uploadFile(fileInput.files[0]);
                source2Type = 'file';
            }

            // 사용자 정의 프롬프트 가져오기
            const customPromptElement = document.getElementById('custom_prompt');
            const customPrompt = customPromptElement ? customPromptElement.value.trim() : '';

            // 비교 분석 요청
            const response = await fetch('/api/analyze/compare', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    source1: source1,
                    source1_type: source1Type,
                    product1_name: product1Name,
                    source2: source2,
                    source2_type: source2Type,
                    product2_name: product2Name,
                    custom_prompt: customPrompt
                })
            });

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error);
            }

            this.currentResults = result;
            this.displayResults(result, 'compare');
            this.showNotification('비교 분석이 완료되었습니다!', 'success');

        } catch (error) {
            console.error('비교 분석 오류:', error);
            this.showNotification(error.message, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error);
        }

        return result.file_path;
    }

    displayResults(result, type) {
        const resultsSection = document.getElementById('resultsSection');
        const analysisResults = document.getElementById('analysisResults');

        if (type === 'individual') {
            analysisResults.innerHTML = this.renderIndividualResults(result);
        } else if (type === 'compare') {
            analysisResults.innerHTML = this.renderComparisonResults(result);
        }

        // 결과 섹션 표시
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth' });

        // 챗봇 버튼 활성화
        document.getElementById('chatbotBtn').disabled = false;
    }

    renderIndividualResults(result) {
        // 원본 텍스트 및 추출 통계 저장
        this.currentRawText = result.content;
        this.currentExtractionStats = result.extraction_stats;
        
        if (result.gpt_used && result.analysis) {
            const parsedAnalysis = this.parseAnalysisContent(result.analysis);
            return this.renderStructuredAnalysis(parsedAnalysis, 'individual');
        } else {
            return this.renderBasicResults(result, 'individual');
        }
    }

    renderComparisonResults(result) {
        if (result.gpt_used && result.comparison_analysis) {
            const parsedComparison = this.parseComparisonContent(result.comparison_analysis);
            return this.renderStructuredComparison(parsedComparison, result);
        } else {
            return this.renderBasicResults(result, 'compare');
        }
    }

    parseAnalysisContent(analysis) {
        console.log('Parsing analysis content:', analysis); // 디버깅용
        
        const sections = {};
        const lines = analysis.split('\n');
        let currentSection = '';
        let content = [];

        for (const line of lines) {
            const trimmed = line.trim();
            
            // 더 유연한 섹션 매칭 (다양한 패턴 추가)
            if (trimmed.includes('📊') && (trimmed.includes('상품') || trimmed.includes('비교') || trimmed.includes('분석'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'header';
                content = [line];
            } else if (trimmed.includes('🏷️') && trimmed.includes('분석:')) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'header';
                content = [line];
            } else if (trimmed.includes('📋') && (trimmed.includes('기본') || trimmed.includes('정보'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'basic_info';
                content = [line];
            } else if (trimmed.includes('💰') && (trimmed.includes('보험료') || trimmed.includes('납입'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'premium_info';
                content = [line];
            } else if (trimmed.includes('🛡️') && (trimmed.includes('보장') || trimmed.includes('담보'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'coverage';
                content = [line];
            } else if (trimmed.includes('✅') && (trimmed.includes('장점') || trimmed.includes('우위'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'advantages';
                content = [line];
            } else if (trimmed.includes('💸') && (trimmed.includes('해약') || trimmed.includes('환급'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'refund';
                content = [line];
            } else if (trimmed.includes('👥') && (trimmed.includes('대상') || trimmed.includes('고객'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'target';
                content = [line];
            } else if (trimmed.includes('⭐') && (trimmed.includes('평가') || trimmed.includes('점수'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'score';
                content = [line];
            // 텍스트 기반 섹션 매칭 (이모지가 없는 경우)
            } else if (trimmed.match(/^##?\s*(기본|상품)\s*(정보|개요)/i)) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'basic_info';
                content = [line];
            } else if (trimmed.match(/^##?\s*(보험료|납입)\s*(정보|내용)/i)) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'premium_info';
                content = [line];
            } else if (trimmed.match(/^##?\s*(보장|담보)\s*(내용|정보)/i)) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'coverage';
                content = [line];
            } else if (trimmed.match(/^##?\s*(장점|우위|특징)/i)) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'advantages';
                content = [line];
            } else if (trimmed.match(/^##?\s*(해약|환급)/i)) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'refund';
                content = [line];
            } else if (trimmed.match(/^##?\s*(대상|타겟)\s*(고객|층)/i)) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'target';
                content = [line];
            } else if (trimmed.match(/^##?\s*(평가|점수|종합)/i)) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'header';
                content = [line];
            } else if (trimmed.includes('📋') && trimmed.includes('기본')) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'basic_info';
                content = [];
            } else if (trimmed.includes('💰') && trimmed.includes('보험료')) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'premium_info';
                content = [];
            } else if (trimmed.includes('🛡️') && (trimmed.includes('핵심') || trimmed.includes('보장'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'coverage';
                content = [];
            } else if (trimmed.includes('⭐') && (trimmed.includes('경쟁') || trimmed.includes('우위'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'advantages';
                content = [];
            } else if (trimmed.includes('💎') && (trimmed.includes('해약') || trimmed.includes('환급'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'refund';
                content = [];
            } else if (trimmed.includes('🎯') && (trimmed.includes('추천') || trimmed.includes('대상'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'target';
                content = [];
            } else if (trimmed.includes('📊') && (trimmed.includes('비교') || trimmed.includes('점수') || trimmed.includes('평가'))) {
                if (currentSection && content.length > 0) {
                    sections[currentSection] = content.join('\n');
                }
                currentSection = 'score';
                content = [];
            } else {
                content.push(line);
            }
        }
        
        if (currentSection && content.length > 0) {
            sections[currentSection] = content.join('\n');
        }

        console.log('Parsed sections:', sections); // 디버깅용
        
        // 섹션 파싱에 실패한 경우 전체 텍스트에서 직접 추출
        if (Object.keys(sections).length === 0 || (!sections.basic_info && !sections.premium_info)) {
            console.log('섹션 파싱 실패, 전체 텍스트에서 직접 추출 시도');
            sections.fallback_content = analysis;
            
            // 전체 텍스트에서 기본 정보 추출
            if (!sections.basic_info) {
                sections.basic_info = this.extractBasicInfoFromFullText(analysis);
            }
            
            // 전체 텍스트에서 보험료 정보 추출
            if (!sections.premium_info) {
                sections.premium_info = this.extractPremiumInfoFromFullText(analysis);
            }
        }
        
        return sections;
    }

    parseComparisonContent(comparison) {
        console.log('Parsing comparison content:', comparison); // 디버깅용
        
        // 다양한 구분자로 상품 분리 시도
        let products = [];
        
        if (comparison.includes('상품 B 분석')) {
            products = comparison.split('상품 B 분석');
        } else if (comparison.includes('상품 B')) {
            products = comparison.split('상품 B');
        } else if (comparison.includes('🏷️ 상품 비교 분석: 상품 B')) {
            products = comparison.split('🏷️ 상품 비교 분석: 상품 B');
        } else {
            // 다른 패턴으로 분리 시도
            const lines = comparison.split('\n');
            let productAContent = [];
            let productBContent = [];
            let isProductB = false;
            
            for (const line of lines) {
                if (line.includes('상품 B') || line.includes('B상품') || (line.includes('📊') && line.includes('상품 B'))) {
                    isProductB = true;
                    productBContent.push(line);
                } else if (isProductB) {
                    productBContent.push(line);
                } else {
                    productAContent.push(line);
                }
            }
            
            products = [productAContent.join('\n'), productBContent.join('\n')];
        }
        
        const productA = this.parseAnalysisContent(products[0] || '');
        const productB = products.length > 1 ? 
            this.parseAnalysisContent(products[1].includes('상품 B') ? products[1] : '상품 B 분석\n' + products[1]) : 
            {};
        
        console.log('Parsed product A:', productA);
        console.log('Parsed product B:', productB);
        
        return { productA, productB };
    }

    renderStructuredAnalysis(sections, type) {
        const productName = this.extractProductName(sections.header || '');
        const basicInfo = this.parseBasicInfo(sections.basic_info || '');
        const premiumInfo = this.parsePremiumInfo(sections.premium_info || '');
        const coverage = this.parseCoverage(sections.coverage || '');
        const advantages = this.parseAdvantages(sections.advantages || '');
        const refund = this.parseRefund(sections.refund || '');
        const target = this.parseTarget(sections.target || '');
        const score = this.parseScore(sections.score || '');

        return `
            <div class="structured-analysis">
                <!-- Header -->
                <div class="analysis-header">
                    <div class="row align-items-center mb-4">
                        <div class="col-md-8">
                            <h2 class="product-title">
                                <i class="fas fa-shield-alt text-primary me-2"></i>
                                ${productName || '보험상품 분석'}
                            </h2>
                            <p class="text-muted">AI 기반 전문 상품 분석 결과</p>
                        </div>
                        <div class="col-md-4 text-end">
                            <div class="analysis-badge">
                                <span class="badge bg-success fs-6">
                                    <i class="fas fa-brain me-1"></i>GPT 분석 완료
                                </span>
                                ${this.renderExtractionBadges()}
                                <button class="btn btn-outline-secondary btn-sm ms-2" onclick="app.showRawText()">
                                    <i class="fas fa-file-text me-1"></i>원본 텍스트
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Analysis Tabs -->
                <ul class="nav nav-tabs nav-fill mb-4" id="analysisTab" role="tablist">
                    <li class="nav-item" role="presentation">
                        <button class="nav-link active" id="summary-tab" data-bs-toggle="tab" data-bs-target="#summary" type="button" role="tab">
                            <i class="fas fa-chart-pie me-2"></i>분석 요약
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="details-tab" data-bs-toggle="tab" data-bs-target="#details" type="button" role="tab">
                            <i class="fas fa-list-ul me-2"></i>상세 내용
                        </button>
                    </li>
                    <li class="nav-item" role="presentation">
                        <button class="nav-link" id="rawtext-tab" data-bs-toggle="tab" data-bs-target="#rawtext" type="button" role="tab">
                            <i class="fas fa-file-text me-2"></i>원본 텍스트
                        </button>
                    </li>
                </ul>

                <!-- Tab Content -->
                <div class="tab-content" id="analysisTabContent">
                    <!-- Summary Tab -->
                    <div class="tab-pane fade show active" id="summary" role="tabpanel">
                        <div class="row g-4">
                            <!-- Left Column -->
                            <div class="col-lg-8">
                                <!-- Basic Info Card -->
                                ${this.renderInfoCard('기본 정보', 'info-circle', 'primary', basicInfo)}
                                
                                <!-- Coverage Card -->
                                ${this.renderCoverageCard(coverage)}
                                
                                <!-- Advantages Card -->
                                ${this.renderAdvantagesCard(advantages)}
                            </div>

                            <!-- Right Column -->
                            <div class="col-lg-4">
                                <!-- Premium Info Card -->
                                ${this.renderPremiumCard(premiumInfo)}
                                
                                <!-- Score Card -->
                                ${this.renderScoreCard(score)}
                                
                                <!-- Target Card -->
                                ${this.renderTargetCard(target)}
                                
                                <!-- Refund Card -->
                                ${this.renderRefundCard(refund)}
                            </div>
                        </div>
                    </div>

                    <!-- Details Tab -->
                    <div class="tab-pane fade" id="details" role="tabpanel">
                        ${this.renderDetailedContent(sections)}
                    </div>

                    <!-- Raw Text Tab -->
                    <div class="tab-pane fade" id="rawtext" role="tabpanel">
                        ${this.renderRawTextContent()}
                    </div>
                </div>
            </div>
        `;
    }

    renderStructuredComparison(parsedComparison, result) {
        return `
            <div class="structured-comparison">
                <!-- Header -->
                <div class="comparison-header mb-4">
                    <h2 class="text-center mb-3">
                        <i class="fas fa-balance-scale text-primary me-2"></i>
                        2개 상품 비교 분석
                    </h2>
                    <div class="comparison-meta text-center">
                        <span class="badge bg-primary me-2">${result.product1.name}: ${result.product1.page_count}페이지</span>
                        <span class="badge bg-secondary me-2">${result.product2.name}: ${result.product2.page_count}페이지</span>
                        <span class="badge bg-success">GPT 비교 분석 완료</span>
                    </div>
                </div>

                <!-- Comparison Grid -->
                <div class="row g-4">
                    <div class="col-lg-6">
                        <div class="product-comparison-card border-primary">
                            <div class="card-header bg-primary text-white">
                                <h4 class="mb-0">
                                    <i class="fas fa-file-alt me-2"></i>상품 A
                                </h4>
                            </div>
                            <div class="card-body">
                                ${this.renderComparisonContent(parsedComparison.productA)}
                            </div>
                        </div>
                    </div>
                    <div class="col-lg-6">
                        <div class="product-comparison-card border-secondary">
                            <div class="card-header bg-secondary text-white">
                                <h4 class="mb-0">
                                    <i class="fas fa-file-alt me-2"></i>상품 B
                                </h4>
                            </div>
                            <div class="card-body">
                                ${this.renderComparisonContent(parsedComparison.productB)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderInfoCard(title, icon, color, content) {
        return `
            <div class="info-card mb-4">
                <div class="card h-100">
                    <div class="card-header bg-${color} text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-${icon} me-2"></i>${title}
                        </h5>
                    </div>
                    <div class="card-body">
                        <div class="info-grid">
                            ${this.formatInfoContent(content)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderPremiumCard(premiumInfo) {
        return `
            <div class="premium-card mb-4">
                <div class="card h-100 border-warning">
                    <div class="card-header bg-warning text-dark">
                        <h5 class="mb-0">
                            <i class="fas fa-won-sign me-2"></i>보험료 정보
                        </h5>
                    </div>
                    <div class="card-body">
                        ${this.formatPremiumInfo(premiumInfo)}
                    </div>
                </div>
            </div>
        `;
    }

    renderCoverageCard(coverage) {
        return `
            <div class="coverage-card mb-4">
                <div class="card h-100">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-shield-alt me-2"></i>보장 내용
                        </h5>
                    </div>
                    <div class="card-body">
                        ${this.formatCoverageContent(coverage)}
                    </div>
                </div>
            </div>
        `;
    }

    renderScoreCard(score) {
        return `
            <div class="score-card mb-4">
                <div class="card h-100 border-info">
                    <div class="card-header bg-info text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-star me-2"></i>종합 평가
                        </h5>
                    </div>
                    <div class="card-body">
                        ${this.formatScoreContent(score)}
                    </div>
                </div>
            </div>
        `;
    }

    renderAdvantagesCard(advantages) {
        return `
            <div class="advantages-card mb-4">
                <div class="card h-100">
                    <div class="card-header bg-danger text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-trophy me-2"></i>경쟁 우위
                        </h5>
                    </div>
                    <div class="card-body">
                        ${this.formatAdvantagesContent(advantages)}
                    </div>
                </div>
            </div>
        `;
    }

    renderTargetCard(target) {
        return `
            <div class="target-card mb-4">
                <div class="card h-100 border-dark">
                    <div class="card-header bg-dark text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-users me-2"></i>추천 대상
                        </h5>
                    </div>
                    <div class="card-body">
                        ${this.formatTargetContent(target)}
                    </div>
                </div>
            </div>
        `;
    }

    renderRefundCard(refund) {
        return `
            <div class="refund-card mb-4">
                <div class="card h-100 border-secondary">
                    <div class="card-header bg-secondary text-white">
                        <h5 class="mb-0">
                            <i class="fas fa-undo me-2"></i>해약/환급
                        </h5>
                    </div>
                    <div class="card-body">
                        ${this.formatRefundContent(refund)}
                    </div>
                </div>
            </div>
        `;
    }

    renderComparisonContent(productData) {
        const productName = this.extractProductName(productData.header || '');
        const basicInfo = this.parseBasicInfo(productData.basic_info || '');
        const premiumInfo = this.parsePremiumInfo(productData.premium_info || '');
        const score = this.parseScore(productData.score || '');

        return `
            <div class="comparison-content">
                <h6 class="text-primary mb-3">${productName}</h6>
                <div class="info-summary mb-3">
                    ${this.formatInfoContent(basicInfo, true)}
                </div>
                <div class="premium-summary mb-3">
                    ${this.formatPremiumInfo(premiumInfo, true)}
                </div>
                <div class="score-summary">
                    ${this.formatScoreContent(score, true)}
                </div>
            </div>
        `;
    }

    renderBasicResults(result, type) {
        // GPT 분석 실패 시에도 구조화된 정보 추출 시도
        console.log('GPT 분석 실패, 원본 텍스트에서 구조화 정보 추출 시도');
        
        const basicInfo = this.extractBasicInfoFromFullText(result.content);
        const premiumInfo = this.extractPremiumInfoFromFullText(result.content);
        
        // 구조화된 정보가 추출되었으면 구조화 표시
        if (basicInfo || premiumInfo) {
            console.log('원본 텍스트에서 구조화 정보 추출 성공');
            
            const mockSections = {
                header: `📊 텍스트 기반 분석 결과`,
                basic_info: basicInfo,
                premium_info: premiumInfo,
                coverage: result.content ? result.content.substring(0, 1000) + '...' : '',  // 첫 1000자를 보장 정보로
                raw_content: result.content
            };
            
            return this.renderStructuredAnalysis(mockSections, type);
        }
        
        // 구조화 실패 시 기본 텍스트 표시
        return `
            <div class="basic-results">
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    GPT 분석을 사용할 수 없어 기본 텍스트 추출 결과를 표시합니다.
                </div>
                <div class="text-content-display">
                    <pre class="formatted-text">${this.escapeHtml(result.content)}</pre>
                </div>
            </div>
        `;
    }

    // Helper methods for parsing and formatting content
    extractProductName(header) {
        console.log('Extracting product name from header:', header); // 디버깅용
        
        if (!header || typeof header !== 'string') {
            return '';
        }
        
        // 다양한 패턴으로 상품명 추출 시도
        let productName = '';
        
        // 🏷️ 패턴
        let match = header.match(/🏷️.*?분석:\s*(.+)/);
        if (match) {
            productName = match[1].trim();
        }
        
        // 📊 패턴  
        if (!productName) {
            match = header.match(/📊.*?분석.*?:\s*(.+)/);
            if (match) {
                productName = match[1].trim();
            }
        }
        
        // 상품 비교 분석: 패턴
        if (!productName) {
            match = header.match(/상품.*?분석.*?:\s*(.+)/);
            if (match) {
                productName = match[1].trim();
            }
        }
        
        // 단순히 : 뒤의 내용
        if (!productName && header.includes(':')) {
            const parts = header.split(':');
            if (parts.length > 1) {
                productName = parts[parts.length - 1].trim();
            }
        }
        
        // 줄바꿈으로 분리된 경우 첫 번째 의미있는 줄 사용
        if (!productName) {
            const lines = header.split('\n');
            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed && !trimmed.includes('📊') && !trimmed.includes('=')) {
                    productName = trimmed;
                    break;
                }
            }
        }
        
        console.log('Extracted product name:', productName); // 디버깅용
        return productName;
    }

    parseBasicInfo(content) {
        console.log('Parsing basic info from:', content); // 디버깅용
        
        const info = {};
        if (!content || typeof content !== 'string') {
            console.log('No content to parse basic info from');
            return info;
        }
        
        // 전체 텍스트에서 패턴 매칭 (더 강력한 정규식 사용)
        const fullText = content.replace(/\n/g, ' ');
        
        // 상품명 추출 (다양한 패턴)
        const namePatterns = [
            /상품명[:：]\s*([^\n\r,]+)/gi,
            /\*\*상품명\*\*[:：]?\s*([^\n\r,]+)/gi,
            /-\s*\*\*상품명\*\*[:：]?\s*([^\n\r,]+)/gi,
            /상품\s*[:：]\s*([^\n\r,]+보험[^\n\r,]*)/gi
        ];
        
        for (const pattern of namePatterns) {
            const match = pattern.exec(fullText);
            if (match && match[1]?.trim()) {
                info.name = match[1].trim().replace(/\*\*/g, '');
                break;
            }
        }
        
        // 상품코드 추출
        const codePatterns = [
            /상품코드[:：]\s*([^\n\r,]+)/gi,
            /\*\*상품코드\*\*[:：]?\s*([^\n\r,]+)/gi,
            /-\s*\*\*상품코드\*\*[:：]?\s*([^\n\r,]+)/gi,
            /코드[:：]\s*([A-Z0-9\-_]+)/gi
        ];
        
        for (const pattern of codePatterns) {
            const match = pattern.exec(fullText);
            if (match && match[1]?.trim()) {
                info.code = match[1].trim().replace(/\*\*/g, '');
                break;
            }
        }
        
        // 상품타입 추출
        const typePatterns = [
            /상품타입[:：]\s*([^\n\r,]+)/gi,
            /\*\*상품타입\*\*[:：]?\s*([^\n\r,]+)/gi,
            /타입[:：]\s*([^\n\r,]+보험[^\n\r,]*)/gi,
            /(어린이보험|종합보험|암보험|건강보험|상해보험)/gi
        ];
        
        for (const pattern of typePatterns) {
            const match = pattern.exec(fullText);
            if (match && match[1]?.trim()) {
                info.type = match[1].trim().replace(/\*\*/g, '');
                break;
            }
        }
        
        // 회사명 추출
        const companyPatterns = [
            /회사[:：]\s*([^\n\r,]+)/gi,
            /\*\*회사\*\*[:：]?\s*([^\n\r,]+)/gi,
            /보험회사[:：]\s*([^\n\r,]+)/gi,
            /(KB|삼성|현대|메리츠|동양|한화|롯데|AIA|알리안츠|처브|MG|DB|푸본현대|흥국|KB손해보험|삼성화재|현대해상)\s*[생명]*[손해]*보험/gi
        ];
        
        for (const pattern of companyPatterns) {
            const match = pattern.exec(fullText);
            if (match && match[1]?.trim()) {
                info.company = match[1].trim().replace(/\*\*/g, '');
                break;
            }
        }
        
        // 기존 라인별 파싱도 병행 (이전 방식 유지)
        const lines = content.split('\n');
        for (const line of lines) {
            const trimmed = line.trim();
            
            // 더 유연한 매칭
            if (trimmed.includes('상품명') && trimmed.includes(':') && !info.name) {
                info.name = trimmed.split(':')[1]?.trim();
            } else if (trimmed.includes('상품코드') && trimmed.includes(':') && !info.code) {
                info.code = trimmed.split(':')[1]?.trim();
            } else if ((trimmed.includes('상품타입') || (trimmed.includes('타입') && trimmed.includes(':'))) && !info.type) {
                info.type = trimmed.split(':')[1]?.trim();
            } else if (trimmed.includes('회사') && trimmed.includes(':') && !info.company) {
                info.company = trimmed.split(':')[1]?.trim();
            }
            
            // 하이픈(-) 으로 시작하는 정보도 파싱
            if (trimmed && trimmed.startsWith('- 상품명:')) {
                info.name = trimmed.substring(trimmed.indexOf(':') + 1).trim();
            } else if (trimmed && trimmed.startsWith('- 상품코드:')) {
                info.code = trimmed.substring(trimmed.indexOf(':') + 1).trim();
            } else if (trimmed && trimmed.startsWith('- 상품타입:')) {
                info.type = trimmed.substring(trimmed.indexOf(':') + 1).trim();
            } else if (trimmed && trimmed.startsWith('- 회사:')) {
                info.company = trimmed.substring(trimmed.indexOf(':') + 1).trim();
            }
        }
        
        console.log('Parsed basic info:', info); // 디버깅용
        return info;
    }

    parsePremiumInfo(content) {
        console.log('Parsing premium info from:', content); // 디버깅용
        
        const info = {};
        if (!content || typeof content !== 'string') {
            console.log('No content to parse premium info from');
            return info;
        }
        
        // 전체 텍스트에서 패턴 매칭 (더 강력한 정규식 사용)
        const fullText = content.replace(/\n/g, ' ');
        
        // 월보험료 추출 (GPT 원본 데이터 보존 우선) - 콤마 포함하여 전체 금액 추출
        const monthlyPatterns = [
            /월보험료[:：]\s*([0-9,]+\s*원)/gi,          // 숫자,콤마,원 패턴 우선
            /\*\*월보험료\*\*[:：]?\s*([0-9,]+\s*원)/gi, // 숫자,콤마,원 패턴 우선
            /-\s*\*\*월보험료\*\*[:：]?\s*([0-9,]+\s*원)/gi, // 숫자,콤마,원 패턴 우선
            /월보험료[:：]\s*([0-9,]+)/gi,               // 숫자,콤마만 (원 없는 경우)
            /\*\*월보험료\*\*[:：]?\s*([0-9,]+)/gi,      // 숫자,콤마만 (원 없는 경우)
            /-\s*\*\*월보험료\*\*[:：]?\s*([0-9,]+)/gi,  // 숫자,콤마만 (원 없는 경우)
            /월납[:：]\s*([0-9,]+\s*원)/gi,
            /보험료[:：]\s*([0-9,]+\s*원)/gi,
            /([0-9,]+)\s*원\s*\(월납\)/gi
        ];
        
        for (const pattern of monthlyPatterns) {
            const match = pattern.exec(fullText);
            if (match && match[1]?.trim()) {
                let amount = match[1].trim().replace(/\*\*/g, '');
                
                // GPT 응답에서 온 완전한 형태는 그대로 보존 (예: "92,540원")
                if (amount.includes('원') || amount.includes(',')) {
                    info.monthly = amount;
                } else {
                    // 숫자만 있는 경우에만 포맷팅 (예: "92540" -> "92,540원")
                    const numericValue = parseInt(amount.replace(/[^0-9]/g, ''));
                    if (!isNaN(numericValue)) {
                        info.monthly = numericValue.toLocaleString() + '원';
                    } else {
                        info.monthly = amount; // 파싱 실패 시 원본 유지
                    }
                }
                break;
            }
        }
        
        // 납입방식 추출
        const methodPatterns = [
            /납입방식[:：]\s*([^\n\r,]+)/gi,
            /\*\*납입방식\*\*[:：]?\s*([^\n\r,]+)/gi,
            /-\s*\*\*납입방식\*\*[:：]?\s*([^\n\r,]+)/gi,
            /납입형태[:：]\s*([^\n\r,]+)/gi,
            /(월납|연납|일시납)/gi
        ];
        
        for (const pattern of methodPatterns) {
            const match = pattern.exec(fullText);
            if (match && match[1]?.trim()) {
                info.method = match[1].trim().replace(/\*\*/g, '');
                break;
            }
        }
        
        // 납입기간 추출
        const periodPatterns = [
            /납입기간[:：]\s*([^\n\r,]+)/gi,
            /\*\*납입기간\*\*[:：]?\s*([^\n\r,]+)/gi,
            /-\s*\*\*납입기간\*\*[:：]?\s*([^\n\r,]+)/gi,
            /([0-9]+년납)/gi,
            /([0-9]+세만기)/gi
        ];
        
        for (const pattern of periodPatterns) {
            const match = pattern.exec(fullText);
            if (match && match[1]?.trim()) {
                info.period = match[1].trim().replace(/\*\*/g, '');
                break;
            }
        }
        
        // 기존 라인별 파싱도 병행 (이전 방식 유지)
        const lines = content.split('\n');
        for (const line of lines) {
            const trimmed = line.trim();
            
            // 월보험료 정보
            if (trimmed && trimmed.includes('월보험료') && trimmed.includes(':') && !info.monthly) {
                info.monthly = trimmed.split(':')[1]?.trim();
            } else if (trimmed && trimmed.startsWith('- 월보험료:') && !info.monthly) {
                info.monthly = trimmed.substring(trimmed.indexOf(':') + 1).trim();
            }
            
            // 납입방식 정보
            if (trimmed && trimmed.includes('납입방식') && trimmed.includes(':') && !info.method) {
                info.method = trimmed.split(':')[1]?.trim();
            } else if (trimmed && trimmed.startsWith('- 납입방식:') && !info.method) {
                info.method = trimmed.substring(trimmed.indexOf(':') + 1).trim();
            }
            
            // 납입기간 정보
            if (trimmed && trimmed.includes('납입기간') && trimmed.includes(':') && !info.period) {
                info.period = trimmed.split(':')[1]?.trim();
            } else if (trimmed && trimmed.startsWith('- 납입기간:') && !info.period) {
                info.period = trimmed.substring(trimmed.indexOf(':') + 1).trim();
            }
        }
        
        console.log('Parsed premium info:', info); // 디버깅용
        return info;
    }

    extractBasicInfoFromFullText(text) {
        console.log('전체 텍스트에서 기본 정보 추출 시도');
        
        // 직접 텍스트 추출을 위한 더 강력한 패턴들
        const patterns = {
            name: [
                /상품명[:：]?\s*([^\n\r,\.]+(?:보험|플러스|특약)[^\n\r,]*)/gi,
                /(\w+\s*(?:보험|플러스)[^\n\r,]*(?:무배당|유배당)?[^\n\r,]*)/gi,
                /(KB|삼성|현대|메리츠)\s*[^\n\r,]*보험[^\n\r,]*/gi
            ],
            code: [
                /상품코드[:：]?\s*([A-Z0-9\-_]+)/gi,
                /코드[:：]?\s*([A-Z0-9\-_]+)/gi,
                /\(([A-Z0-9\-_]{5,})\)/gi
            ],
            type: [
                /(어린이보험|종합보험|암보험|건강보험|상해보험|자녀보험|교육보험)/gi,
                /상품타입[:：]?\s*([^\n\r,]+)/gi
            ],
            company: [
                /(KB|삼성|현대|메리츠|동양|한화|롯데|AIA|알리안츠|처브|MG|DB|푸본현대|흥국)\s*(?:생명|손해|화재)?보험/gi,
                /회사[:：]?\s*([^\n\r,]+)/gi
            ]
        };
        
        const extracted = {};
        
        for (const [key, patternList] of Object.entries(patterns)) {
            for (const pattern of patternList) {
                const match = pattern.exec(text);
                if (match && match[1]?.trim()) {
                    extracted[key] = match[1].trim();
                    break;
                }
            }
        }
        
        console.log('전체 텍스트에서 추출된 기본 정보:', extracted);
        
        // 추출된 정보를 텍스트 형태로 변환
        let result = '';
        if (extracted.name) result += `상품명: ${extracted.name}\n`;
        if (extracted.code) result += `상품코드: ${extracted.code}\n`;
        if (extracted.type) result += `상품타입: ${extracted.type}\n`;
        if (extracted.company) result += `회사: ${extracted.company}\n`;
        
        return result || (text ? text.substring(0, 500) : ''); // fallback으로 첫 500자
    }

    extractPremiumInfoFromFullText(text) {
        console.log('전체 텍스트에서 보험료 정보 추출 시도');
        
        const patterns = {
            monthly: [
                /월보험료[:：]?\s*([0-9,]+\s*원)/gi,
                /월납[:：]?\s*([0-9,]+\s*원)/gi,
                /보험료[:：]?\s*([0-9,]+\s*원)/gi,
                /([0-9,]+)\s*원\s*\(월납\)/gi
            ],
            method: [
                /납입방식[:：]?\s*([^\n\r,]+)/gi,
                /납입형태[:：]?\s*([^\n\r,]+)/gi,
                /(월납|연납|일시납)/gi
            ],
            period: [
                /납입기간[:：]?\s*([^\n\r,]+)/gi,
                /([0-9]+년납)/gi,
                /([0-9]+세만기)/gi,
                /납입.*?([0-9]+년)/gi
            ]
        };
        
        const extracted = {};
        
        for (const [key, patternList] of Object.entries(patterns)) {
            for (const pattern of patternList) {
                const match = pattern.exec(text);
                if (match && match[1]?.trim()) {
                    extracted[key] = match[1].trim();
                    break;
                }
            }
        }
        
        console.log('전체 텍스트에서 추출된 보험료 정보:', extracted);
        
        // 추출된 정보를 텍스트 형태로 변환
        let result = '';
        if (extracted.monthly) result += `월보험료: ${extracted.monthly}\n`;
        if (extracted.method) result += `납입방식: ${extracted.method}\n`;
        if (extracted.period) result += `납입기간: ${extracted.period}\n`;
        
        return result || (text ? text.substring(0, 300) : ''); // fallback으로 첫 300자
    }

    parseCoverage(content) {
        // 보장 내용 파싱 로직
        return content;
    }

    parseAdvantages(content) {
        // 경쟁 우위 파싱 로직
        return content;
    }

    parseRefund(content) {
        // 해약/환급 정보 파싱 로직
        return content;
    }

    parseTarget(content) {
        // 추천 대상 파싱 로직
        return content;
    }

    parseScore(content) {
        // 점수 파싱 로직
        return content;
    }

    formatInfoContent(info, isCompact = false) {
        console.log('Formatting info content:', info); // 디버깅용
        
        if (typeof info === 'string') {
            // 문자열인 경우 직접 표시
            return `<div class="raw-info">${this.formatMarkdown(info)}</div>`;
        }
        
        let html = '';
        let hasAnyInfo = false;
        
        if (info.name) {
            html += `<div class="info-item"><strong>상품명:</strong> ${info.name}</div>`;
            hasAnyInfo = true;
        }
        if (info.code) {
            html += `<div class="info-item"><strong>상품코드:</strong> ${info.code}</div>`;
            hasAnyInfo = true;
        }
        if (info.type) {
            html += `<div class="info-item"><strong>타입:</strong> <span class="badge bg-primary">${info.type}</span></div>`;
            hasAnyInfo = true;
        }
        if (info.company) {
            html += `<div class="info-item"><strong>회사:</strong> ${info.company}</div>`;
            hasAnyInfo = true;
        }
        
        if (!hasAnyInfo) {
            // 기본 정보가 없는 경우 원본 섹션 내용을 표시
            if (typeof info === 'object' && Object.keys(info).length === 0) {
                html = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        구조화된 기본 정보를 추출할 수 없었습니다.
                        <br><small>상세 내용 탭에서 전체 분석 결과를 확인하세요.</small>
                    </div>
                `;
            } else {
                html = '<p class="text-muted">정보를 추출할 수 없습니다.</p>';
            }
        }
        
        return html;
    }

    formatPremiumInfo(info, isCompact = false) {
        console.log('Formatting premium info:', info); // 디버깅용
        
        if (typeof info === 'string') {
            return `<div class="raw-info">${this.formatMarkdown(info)}</div>`;
        }
        
        let html = '';
        let hasAnyInfo = false;
        
        if (info.monthly) {
            html += `<div class="premium-highlight text-center mb-3">
                <h4 class="text-primary">${info.monthly}</h4>
                <small class="text-muted">월 보험료</small>
            </div>`;
            hasAnyInfo = true;
        }
        if (info.method) {
            html += `<div class="info-item"><strong>납입방식:</strong> ${info.method}</div>`;
            hasAnyInfo = true;
        }
        if (info.period) {
            html += `<div class="info-item"><strong>납입기간:</strong> ${info.period}</div>`;
            hasAnyInfo = true;
        }
        
        if (!hasAnyInfo) {
            if (typeof info === 'object' && Object.keys(info).length === 0) {
                html = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        구조화된 보험료 정보를 추출할 수 없었습니다.
                        <br><small>상세 내용 탭에서 전체 분석 결과를 확인하세요.</small>
                    </div>
                `;
            } else {
                html = '<p class="text-muted">보험료 정보를 추출할 수 없습니다.</p>';
            }
        }
        
        return html;
    }

    formatCoverageContent(content) {
        return `<div class="coverage-content">${this.formatMarkdown(content)}</div>`;
    }

    formatAdvantagesContent(content) {
        return `<div class="advantages-content">${this.formatMarkdown(content)}</div>`;
    }

    formatTargetContent(content) {
        return `<div class="target-content">${this.formatMarkdown(content)}</div>`;
    }

    formatRefundContent(content) {
        return `<div class="refund-content">${this.formatMarkdown(content)}</div>`;
    }

    formatScoreContent(content, isCompact = false) {
        return `<div class="score-content">${this.formatMarkdown(content)}</div>`;
    }

    renderDetailedContent(sections) {
        return `
            <div class="detailed-content">
                <div class="row g-4">
                    <div class="col-12">
                        <div class="accordion" id="detailsAccordion">
                            <!-- Coverage Details -->
                            <div class="accordion-item">
                                <h2 class="accordion-header" id="coverageDetails">
                                    <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#collapseCoverage">
                                        <i class="fas fa-shield-alt text-success me-2"></i>
                                        보장 내용 상세
                                    </button>
                                </h2>
                                <div id="collapseCoverage" class="accordion-collapse collapse show" data-bs-parent="#detailsAccordion">
                                    <div class="accordion-body">
                                        ${this.formatMarkdown(sections.coverage || '보장 내용 정보가 없습니다.')}
                                    </div>
                                </div>
                            </div>

                            <!-- Advantages Details -->
                            <div class="accordion-item">
                                <h2 class="accordion-header" id="advantagesDetails">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseAdvantages">
                                        <i class="fas fa-trophy text-danger me-2"></i>
                                        경쟁 우위 상세
                                    </button>
                                </h2>
                                <div id="collapseAdvantages" class="accordion-collapse collapse" data-bs-parent="#detailsAccordion">
                                    <div class="accordion-body">
                                        ${this.formatMarkdown(sections.advantages || '경쟁 우위 정보가 없습니다.')}
                                    </div>
                                </div>
                            </div>

                            <!-- Target Details -->
                            <div class="accordion-item">
                                <h2 class="accordion-header" id="targetDetails">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseTarget">
                                        <i class="fas fa-users text-dark me-2"></i>
                                        추천 대상 상세
                                    </button>
                                </h2>
                                <div id="collapseTarget" class="accordion-collapse collapse" data-bs-parent="#detailsAccordion">
                                    <div class="accordion-body">
                                        ${this.formatMarkdown(sections.target || '추천 대상 정보가 없습니다.')}
                                    </div>
                                </div>
                            </div>

                            <!-- Refund Details -->
                            <div class="accordion-item">
                                <h2 class="accordion-header" id="refundDetails">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseRefund">
                                        <i class="fas fa-undo text-secondary me-2"></i>
                                        해약/환급 상세
                                    </button>
                                </h2>
                                <div id="collapseRefund" class="accordion-collapse collapse" data-bs-parent="#detailsAccordion">
                                    <div class="accordion-body">
                                        ${this.formatMarkdown(sections.refund || '해약/환급 정보가 없습니다.')}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderRawTextContent() {
        // 현재 분석 결과에서 원본 텍스트를 가져옴
        const rawText = this.currentRawText || '원본 텍스트를 찾을 수 없습니다.';
        const structuredText = this.structureRawText(rawText);
        
        return `
            <div class="raw-text-content">
                <div class="text-structure-controls mb-3">
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-outline-primary active" onclick="app.showStructuredText()">
                            <i class="fas fa-list me-1"></i>구조화된 텍스트
                        </button>
                        <button type="button" class="btn btn-outline-secondary" onclick="app.showOriginalText()">
                            <i class="fas fa-file-text me-1"></i>원본 텍스트
                        </button>
                    </div>
                    <div class="text-search-box ms-3 d-inline-block">
                        <div class="input-group input-group-sm" style="width: 250px;">
                            <input type="text" class="form-control" placeholder="텍스트 검색..." id="textSearchInput">
                            <button class="btn btn-outline-primary" type="button" onclick="app.searchInText()">
                                <i class="fas fa-search"></i>
                            </button>
                        </div>
                    </div>
                </div>
                
                <div id="structuredTextView" class="text-view">
                    ${structuredText}
                </div>
                
                <div id="originalTextView" class="text-view" style="display: none;">
                    <div class="original-text-container">
                        <pre class="formatted-text">${this.escapeHtml(rawText)}</pre>
                    </div>
                </div>
            </div>
        `;
    }

    structureRawText(rawText) {
        if (!rawText || typeof rawText !== 'string') {
            return '<p class="text-muted">텍스트 내용이 없습니다.</p>';
        }

        const pages = rawText.split('--- 페이지');
        let structuredHTML = '';

        for (let i = 0; i < pages.length; i++) {
            if (pages[i].trim() === '') continue;
            
            const pageContent = pages[i].trim();
            const pageNumber = i > 0 ? i : 1;
            
            // 페이지별로 구조화
            const structuredPage = this.structurePage(pageContent, pageNumber);
            structuredHTML += structuredPage;
        }

        return structuredHTML || '<p class="text-muted">구조화할 텍스트 내용이 없습니다.</p>';
    }

    structurePage(pageContent, pageNumber) {
        const lines = pageContent.split('\n');
        let structuredContent = '';
        
        // 페이지 헤더
        structuredContent += `
            <div class="page-structure mb-4">
                <div class="page-header">
                    <h5 class="text-primary">
                        <i class="fas fa-file-alt me-2"></i>페이지 ${pageNumber}
                    </h5>
                </div>
                <div class="page-content">
        `;

        let currentSection = '';
        let sectionContent = [];

        for (const line of lines) {
            const trimmedLine = line.trim();
            
            if (trimmedLine === '') {
                if (sectionContent.length > 0) {
                    structuredContent += this.renderTextSection(currentSection, sectionContent);
                    sectionContent = [];
                }
                continue;
            }

            // 섹션 식별
            if (this.isHeaderLine(trimmedLine)) {
                if (sectionContent.length > 0) {
                    structuredContent += this.renderTextSection(currentSection, sectionContent);
                }
                currentSection = trimmedLine;
                sectionContent = [];
            } else {
                sectionContent.push(line);
            }
        }

        // 마지막 섹션 처리
        if (sectionContent.length > 0) {
            structuredContent += this.renderTextSection(currentSection, sectionContent);
        }

        structuredContent += `
                </div>
            </div>
        `;

        return structuredContent;
    }

    isHeaderLine(line) {
        // 헤더 라인 식별 로직
        return (
            line.includes('보험') ||
            line.includes('상품') ||
            line.includes('담보') ||
            line.includes('특약') ||
            line.includes('보장') ||
            line.includes('가입') ||
            line.includes('계약') ||
            /^[가-힣\s]+:/.test(line) ||
            line.length < 30 && !line.includes('원') && !line.includes('%')
        );
    }

    renderTextSection(header, content) {
        if (content.length === 0) return '';
        
        const contentText = content.join('\n');
        const isTableContent = this.isTableContent(contentText);
        
        return `
            <div class="text-section mb-3">
                ${header ? `<h6 class="section-header text-dark">${this.escapeHtml(header)}</h6>` : ''}
                <div class="section-content ${isTableContent ? 'table-content' : 'text-content'}">
                    ${isTableContent ? this.renderTableContent(contentText) : `<pre class="formatted-content">${this.escapeHtml(contentText)}</pre>`}
                </div>
            </div>
        `;
    }

    isTableContent(content) {
        // 표 형태 컨텐츠 식별
        const lines = content.split('\n');
        const tableIndicators = lines.filter(line => 
            line.includes('|') || 
            line.includes('원') || 
            line.includes('%') ||
            /\d+/.test(line)
        );
        
        return tableIndicators.length > lines.length * 0.3;
    }

    renderTableContent(content) {
        const lines = content.split('\n').filter(line => line.trim() !== '');
        
        if (lines.length === 0) return '';
        
        // 간단한 표 형태로 렌더링
        let tableHTML = '<div class="table-responsive"><table class="table table-sm table-bordered">';
        
        for (const line of lines) {
            const trimmedLine = line.trim();
            if (trimmedLine === '') continue;
            
            // 파이프(|)로 구분된 경우
            if (trimmedLine.includes('|')) {
                const cells = trimmedLine.split('|').map(cell => cell.trim());
                tableHTML += '<tr>';
                for (const cell of cells) {
                    if (cell !== '') {
                        tableHTML += `<td>${this.escapeHtml(cell)}</td>`;
                    }
                }
                tableHTML += '</tr>';
            } else {
                // 일반 텍스트 라인
                tableHTML += `<tr><td colspan="100%">${this.escapeHtml(trimmedLine)}</td></tr>`;
            }
        }
        
        tableHTML += '</table></div>';
        return tableHTML;
    }

    // 텍스트 뷰 전환 메서드
    showStructuredText() {
        document.getElementById('structuredTextView').style.display = 'block';
        document.getElementById('originalTextView').style.display = 'none';
        
        // 버튼 상태 업데이트
        document.querySelectorAll('.text-structure-controls .btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('.text-structure-controls .btn')[0].classList.add('active');
    }

    showOriginalText() {
        document.getElementById('structuredTextView').style.display = 'none';
        document.getElementById('originalTextView').style.display = 'block';
        
        // 버튼 상태 업데이트
        document.querySelectorAll('.text-structure-controls .btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelectorAll('.text-structure-controls .btn')[1].classList.add('active');
    }

    // 텍스트 검색 기능
    searchInText() {
        const searchTerm = document.getElementById('textSearchInput').value.trim();
        if (!searchTerm) return;
        
        const activeView = document.getElementById('structuredTextView').style.display !== 'none' 
            ? 'structuredTextView' 
            : 'originalTextView';
        
        const viewElement = document.getElementById(activeView);
        const textContent = viewElement.textContent;
        
        // 간단한 하이라이트 기능
        if (textContent.includes(searchTerm)) {
            const regex = new RegExp(`(${this.escapeRegex(searchTerm)})`, 'gi');
            const highlightedHTML = viewElement.innerHTML.replace(regex, '<mark>$1</mark>');
            viewElement.innerHTML = highlightedHTML;
            
            // 첫 번째 결과로 스크롤
            const firstMatch = viewElement.querySelector('mark');
            if (firstMatch) {
                firstMatch.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }
    }

    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    renderExtractionBadges() {
        if (!this.currentExtractionStats) {
            return '';
        }
        
        const stats = this.currentExtractionStats;
        let badges = '<div class="extraction-badges mt-2">';
        
        // OCR 향상 배지
        if (stats.ocr_enhanced_pages > 0) {
            badges += `
                <span class="badge bg-warning text-dark me-1">
                    <i class="fas fa-eye me-1"></i>OCR: ${stats.ocr_enhanced_pages}페이지
                </span>
            `;
        }
        
        // 하이브리드 추출 배지
        if (stats.hybrid_pages > 0) {
            badges += `
                <span class="badge bg-info me-1">
                    <i class="fas fa-layer-group me-1"></i>하이브리드: ${stats.hybrid_pages}페이지
                </span>
            `;
        }
        
        // 전체 커버리지 배지
        const coverage = ((stats.pages_with_text / stats.total_pages) * 100).toFixed(1);
        const coverageColor = coverage >= 90 ? 'success' : coverage >= 70 ? 'warning' : 'danger';
        
        badges += `
            <span class="badge bg-${coverageColor} me-1">
                <i class="fas fa-percentage me-1"></i>추출률: ${coverage}%
            </span>
        `;
        
        badges += '</div>';
        return badges;
    }

    formatMarkdown(text) {
        // 간단한 마크다운 형식 변환
        return text
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatCurrency(amount) {
        if (!amount) return amount;
        
        // 이미 '원'이 포함되어 있으면 그대로 반환 (가장 중요!)
        if (amount.includes('원')) {
            return amount;
        }
        
        // 숫자와 콤마만 추출 (콤마 보존)
        const cleanAmount = amount.replace(/[^0-9,]/g, '');
        
        if (!cleanAmount) return amount;
        
        // 콤마가 이미 있으면 그대로 사용, 없으면 숫자를 천단위로 포맷
        if (cleanAmount.includes(',')) {
            // 이미 포맷된 숫자 (예: "92,540")
            return cleanAmount + '원';
        } else {
            // 포맷되지 않은 숫자 (예: "92540")
            const value = parseInt(cleanAmount);
            if (!isNaN(value)) {
                return value.toLocaleString() + '원';
            }
        }
        
        // 파싱 실패 시 원본 반환
        return amount;
    }

    async showRawText() {
        try {
            // 현재 분석된 상품의 소스 정보 가져오기
            const lastAnalysis = this.getLastAnalysisSource();
            if (!lastAnalysis) {
                alert('분석된 상품이 없습니다. 먼저 상품을 분석해주세요.');
                return;
            }

            const response = await fetch('/api/get_raw_text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source: lastAnalysis.source,
                    source_type: lastAnalysis.source_type
                })
            });

            const result = await response.json();
            
            if (result.success) {
                // 모달에 원본 텍스트 표시
                this.displayRawTextModal(result.raw_text, result.page_count, result.extraction_stats);
            } else {
                alert('원본 텍스트를 가져오는데 실패했습니다: ' + result.error);
            }
        } catch (error) {
            console.error('원본 텍스트 요청 오류:', error);
            alert('원본 텍스트를 가져오는 중 오류가 발생했습니다.');
        }
    }

    getLastAnalysisSource() {
        // 마지막으로 분석한 상품의 소스 정보 반환
        // 임시로 URL 사용 (실제로는 세션에서 가져와야 함)
        return {
            source: 'http://goodrichplus.kr/WdqnG',
            source_type: 'url'
        };
    }

    displayRawTextModal(rawText, pageCount, extractionStats) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'rawTextModal';
        modal.innerHTML = `
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-file-text me-2"></i>원본 텍스트
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <span class="badge bg-info me-2">페이지 수: ${pageCount}</span>
                            ${extractionStats ? this.renderExtractionStatsInModal(extractionStats) : ''}
                        </div>
                        <div class="raw-text-container" style="max-height: 70vh; overflow-y: auto;">
                            <pre class="bg-light p-3 border rounded" style="white-space: pre-wrap; font-size: 12px;">${this.escapeHtml(rawText)}</pre>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">닫기</button>
                        <button type="button" class="btn btn-primary" onclick="app.downloadRawText('${this.escapeHtml(rawText)}')">
                            <i class="fas fa-download me-1"></i>다운로드
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // 모달이 닫힐 때 DOM에서 제거
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    renderExtractionStatsInModal(stats) {
        let badges = '';
        if (stats.ocr_enhanced_pages > 0) {
            badges += `<span class="badge bg-warning text-dark me-1">OCR: ${stats.ocr_enhanced_pages}페이지</span>`;
        }
        if (stats.hybrid_pages > 0) {
            badges += `<span class="badge bg-info me-1">하이브리드: ${stats.hybrid_pages}페이지</span>`;
        }
        const coverage = ((stats.pages_with_text / stats.total_pages) * 100).toFixed(1);
        const coverageColor = coverage >= 90 ? 'success' : coverage >= 70 ? 'warning' : 'danger';
        badges += `<span class="badge bg-${coverageColor} me-1">추출률: ${coverage}%</span>`;
        return badges;
    }

    downloadRawText(text) {
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `raw_text_${new Date().getTime()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // 챗봇 관련 메서드
    sendChatMessage() {
        const chatInput = document.getElementById('chatInput');
        const message = chatInput.value.trim();

        if (!message) return;

        // 사용자 메시지 표시
        this.addChatMessage('사용자', message, 'user');
        chatInput.value = '';

        // 서버로 메시지 전송
        this.socket.emit('chat_message', { message: message });
    }

    handleChatResponse(data) {
        if (data.loading) {
            this.addChatMessage('AI 상담', data.message, 'bot', true);
        } else if (data.error) {
            this.addChatMessage('AI 상담', data.error, 'bot error');
        } else {
            // 기존 로딩 메시지 제거
            this.removeLoadingMessage();
            this.addChatMessage('AI 상담', data.response, 'bot');
        }
    }

    addChatMessage(sender, message, type, isLoading = false) {
        const chatMessages = document.getElementById('chatMessages');
        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${type.includes('user') ? 'user' : 'bot'}`;
        
        if (isLoading) {
            messageElement.id = 'loading-message';
        }

        const contentClass = type.includes('error') ? 'message-content error' : 'message-content';
        
        messageElement.innerHTML = `
            <div class="${contentClass}">
                <div class="message-sender">${sender}</div>
                <div class="message-text">${isLoading ? message : this.formatMarkdown(message)}</div>
                ${isLoading ? '<div class="spinner-border spinner-border-sm mt-2"></div>' : ''}
            </div>
        `;

        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    removeLoadingMessage() {
        const loadingMessage = document.getElementById('loading-message');
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }

    // UI 관련 메서드
    showLoading(message = '처리 중...') {
        const overlay = document.getElementById('loadingOverlay');
        const messageElement = document.getElementById('loadingMessage');
        
        if (messageElement) {
            messageElement.textContent = message;
        }
        
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }

    showNotification(message, type = 'info') {
        // Toast 알림 생성
        const toastContainer = this.getOrCreateToastContainer();
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${this.getBootstrapColorClass(type)} border-0`;
        toast.setAttribute('role', 'alert');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${this.getIconClass(type)} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);

        // Bootstrap Toast 초기화 및 표시
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();

        // 토스트가 숨겨진 후 DOM에서 제거
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    getOrCreateToastContainer() {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed top-0 end-0 p-3';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        return container;
    }

    getBootstrapColorClass(type) {
        const colorMap = {
            'success': 'success',
            'error': 'danger',
            'warning': 'warning',
            'info': 'primary'
        };
        return colorMap[type] || 'primary';
    }

    getIconClass(type) {
        const iconMap = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return iconMap[type] || 'info-circle';
    }
}

// 전역 함수들
function openChatbot() {
    const modal = new bootstrap.Modal(document.getElementById('chatbotModal'));
    modal.show();
}

function downloadResults() {
    if (!window.pdfAnalyzer || !window.pdfAnalyzer.currentResults) {
        alert('다운로드할 결과가 없습니다.');
        return;
    }

    const results = window.pdfAnalyzer.currentResults;
    let content = '';

    if (results.analysis) {
        content = results.analysis;
    } else if (results.comparison_analysis) {
        content = results.comparison_analysis;
    } else {
        content = '분석 결과가 없습니다.';
    }

    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `분석결과_${new Date().toISOString().slice(0, 10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// 애플리케이션 초기화
document.addEventListener('DOMContentLoaded', () => {
    window.pdfAnalyzer = new PDFAnalyzer();
});
