let cachedImages = [];
let displayedImages = [];
let cachedTextFiles = [];
let displayedTextFiles = [];
let selectedImages = new Set();
let lastSelectedIndex = -1;
let currentImageIndex = 0;
let lastUpdateTime = 0;
let isReversed = false;
let currentSortCriteria = 'date-desc';
let textSortCriteria = 'date-desc';
let isTextReversed = false;
let serverConnected = true;
let preventSingleClick = false;
let clickTimer = null;
let selectionStartIndex = -1;
let isSelecting = false;
let newImages = new Set();
let lastImageCount = 0;
let selectedWorkflowPath = null;

const sortFunctions = {
    'date-desc': (a, b) => new Date(b.date) - new Date(a.date),
    'name-asc': (a, b) => a.name.localeCompare(b.name),
    'size-desc': (a, b) => {
        const sizeA = a.size || 0;
        const sizeB = b.size || 0;
        return sizeB - sizeA;
    },
    'type': (a, b) => {
        const typeA = a.name.split('.').pop().toLowerCase();
        const typeB = b.name.split('.').pop().toLowerCase();
        return typeA.localeCompare(typeB);
    }
};

document.addEventListener('DOMContentLoaded', async () => {
    // Set initial view based on saved preference
    const preferredView = localStorage.getItem('preferredView') || 'image';
    
    // Initialize sort buttons
    const imageSortBtn = document.querySelector(`[data-sort="${currentSortCriteria}"]`);
    if (imageSortBtn) imageSortBtn.classList.add('active');
    
    const textSortBtn = document.querySelector(`#textGalleryView [data-sort="${textSortCriteria}"]`);
    if (textSortBtn) textSortBtn.classList.add('active');
    
    // Load initial content
    if (preferredView === 'image') {
        await loadImages(true);
    } else {
        await loadTextFiles(true);
    }
    
    toggleView(preferredView);
    
    // Start periodic refresh
    setInterval(() => {
        if (document.visibilityState === 'visible') {
            const currentView = localStorage.getItem('preferredView') || 'image';
            if (currentView === 'image') {
                loadImages();
            } else {
                loadTextFiles();
            }
        }
    }, UPDATE_INTERVAL);
    
    // Add click handler for workflow modal close
    document.getElementById('workflowModal').addEventListener('click', (event) => {
        if (event.target === event.currentTarget) {
            closeWorkflowModal();
        }
    });
    
    // Initialize side panel
    initializeSidePanel();

    // Add click handlers for all modals
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', handleModalClick);
    });
});

function toggleView(viewType) {
    const imageGalleryView = document.getElementById('imageGalleryView');
    const textGalleryView = document.getElementById('textGalleryView');
    const imageBtn = document.getElementById('imageViewBtn');
    const textBtn = document.getElementById('textViewBtn');
    
    if (viewType === 'image') {
        imageGalleryView.classList.add('active');
        textGalleryView.classList.remove('active');
        imageBtn.classList.add('active');
        textBtn.classList.remove('active');
        loadImages(true);  // Force reload images
    } else {
        imageGalleryView.classList.remove('active');
        textGalleryView.classList.add('active');
        imageBtn.classList.remove('active');
        textBtn.classList.add('active');
        loadTextFiles(true);  // Force reload text files
    }
    
    localStorage.setItem('preferredView', viewType);
}

async function sortAndDisplayTextFiles(clearGallery = false) {
    const gallery = document.getElementById('textGallery');
    if (!gallery) return;

    const filesToSort = [...displayedTextFiles];
    
    if (!filesToSort.length) {
        gallery.innerHTML = '<div class="gallery-message">No text files found in the output directory</div>';
        return;
    }

    // Sort files
    const sortFn = sortFunctions[textSortCriteria];
    if (sortFn) {
        filesToSort.sort(sortFn);
    }

    if (isTextReversed) {
        filesToSort.reverse();
    }

    // Update display
    if (clearGallery) {
        gallery.innerHTML = '';
        filesToSort.forEach((file, index) => {
            const card = createTextCard(file, index);
            gallery.appendChild(card);
        });
    }

    displayedTextFiles = filesToSort;
}

function createTextCard(textFile, index) {
    const formattedName = formatFilename(textFile.name);
    const formattedDate = formatDate(textFile.date);
    
    const card = document.createElement('div');
    card.className = 'text-card';
    card.dataset.filePath = textFile.path;
    card.dataset.index = index;
    
    card.innerHTML = `
        <div class="card-content">
            <div class="text-preview-container">
                <pre class="text-preview">${escapeHtml(textFile.preview)}</pre>
            </div>
            <div class="text-info">
                <div class="formatted-filename">${formattedName}</div>
                <div class="formatted-date">${formattedDate}</div>
            </div>
        </div>
    `;

    // Add click handlers
    card.addEventListener('click', (event) => handleTextCardClick(event, textFile, card));
    card.addEventListener('contextmenu', (event) => showContextMenu(event, textFile, card));

    return card;
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

async function loadImages(force = false) {
    const now = Date.now();
    if (!force && now - lastUpdateTime < UPDATE_INTERVAL) {
        return;
    }

    try {
        console.log('Loading images...');
        const response = await fetch('/api/images');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const fetchedImages = await response.json();
        console.log(`Fetched ${fetchedImages.length} images`);
        
        if (force || imagesHaveChanged(cachedImages, fetchedImages)) {
            cachedImages = fetchedImages;
            displayedImages = [...fetchedImages];
            await sortAndDisplayImages(true);
            lastUpdateTime = now;
            updateServerStatus(true);
        }
    } catch (error) {
        console.error('Error loading images:', error);
        updateServerStatus(false);
    }
}

async function loadTextFiles(force = false) {
    const now = Date.now();
    if (!force && now - lastUpdateTime < UPDATE_INTERVAL) {
        return;
    }

    try {
        console.log('Loading text files...');
        const response = await fetch('/api/text-files');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const fetchedFiles = await response.json();
        console.log(`Fetched ${fetchedFiles.length} text files`);
        
        if (force || filesHaveChanged(cachedTextFiles, fetchedFiles)) {
            cachedTextFiles = fetchedFiles;
            displayedTextFiles = [...fetchedFiles];
            await sortAndDisplayTextFiles(true);
            lastUpdateTime = now;
            updateServerStatus(true);
        }
    } catch (error) {
        console.error('Error loading text files:', error);
        updateServerStatus(false);
    }
}

async function sortAndDisplayImages(clearGallery = false) {
    const gallery = document.getElementById('gallery');
    if (!gallery) return;

    const imagesToSort = [...displayedImages];
    
    if (!imagesToSort.length) {
        gallery.innerHTML = '<div class="gallery-message">No images found in the output directory</div>';
        return;
    }

    // Sort images
    const sortFn = sortFunctions[currentSortCriteria];
    if (sortFn) {
        imagesToSort.sort(sortFn);
    }

    if (isReversed) {
        imagesToSort.reverse();
    }

    // Update display
    if (clearGallery) {
        gallery.innerHTML = '';
        imagesToSort.forEach((image, index) => {
            const card = createImageCard(image, index);
            gallery.appendChild(card);
        });
    }

    displayedImages = imagesToSort;
}

function createImageCard(image, index) {
    const formattedName = formatFilename(image.name);
    const formattedDate = formatDate(image.date);
    
    const card = document.createElement('div');
    card.className = 'image-card';
    card.dataset.imagePath = image.path;
    card.dataset.index = index;
    
    card.innerHTML = `
        <div class="card-content">
            <div class="image-container">
                <img class="thumbnail" 
                     src="${image.thumbnail || `/output/${image.path}`}" 
                     alt="${formattedName}">
            </div>
            <div class="image-info">
                <div class="formatted-filename">${formattedName}</div>
                <div class="formatted-date">${formattedDate}</div>
            </div>
        </div>
    `;

    // Add click handlers
    card.addEventListener('click', (event) => handleCardClick(event, image, card));
    card.addEventListener('dblclick', (event) => handleCardDoubleClick(event, image, card));

    return card;
}

function updateServerStatus(connected) {
    const statusElement = document.getElementById('serverStatus');
    if (!statusElement) return;
    
    const statusText = statusElement.querySelector('.status-text');
    if (!statusText) return;
    
    serverConnected = connected;
    
    if (connected) {
        statusElement.classList.remove('disconnected');
        statusText.textContent = 'Connected';
    } else {
        statusElement.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }
}

function formatFilename(filename) {
    return filename
        .replace(/\.[^/.]+$/, '')  // Remove extension
        .replace(/_/g, ' ')        // Replace underscores with spaces
        .replace(/(\d+)$/, ' #$1') // Add space before trailing numbers
        .trim();
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function handleCardClick(event, image, card) {
    const currentIndex = parseInt(card.dataset.index);

    if (event.ctrlKey || event.metaKey) {
        // Multi-select with Ctrl/Cmd
        card.classList.toggle('selected');
        if (card.classList.contains('selected')) {
            selectedImages.add(image.path);
            if (selectionStartIndex === -1) {
                selectionStartIndex = currentIndex;
                isSelecting = true;
            }
        } else {
            selectedImages.delete(image.path);
            if (currentIndex === selectionStartIndex) {
                const selectedCards = Array.from(document.querySelectorAll('.image-card.selected'));
                if (selectedCards.length > 0) {
                    selectionStartIndex = parseInt(selectedCards[0].dataset.index);
                } else {
                    selectionStartIndex = -1;
                    isSelecting = false;
                }
            }
        }
        lastSelectedIndex = currentIndex;
    } else if (event.shiftKey) {
        if (selectionStartIndex === -1) {
            selectionStartIndex = currentIndex;
            isSelecting = true;
            card.classList.add('selected');
            selectedImages.add(image.path);
        } else {
            const start = Math.min(selectionStartIndex, currentIndex);
            const end = Math.max(selectionStartIndex, currentIndex);

            const cards = Array.from(document.querySelectorAll('.image-card'));
            cards.forEach((c, i) => {
                if (i >= start && i <= end) {
                    c.classList.add('selected');
                    selectedImages.add(c.dataset.imagePath);
                } else {
                    c.classList.remove('selected');
                    selectedImages.delete(c.dataset.imagePath);
                }
            });
        }
        lastSelectedIndex = currentIndex;
    } else {
        clearSelection();
        card.classList.add('selected');
        selectedImages.add(image.path);
        selectionStartIndex = currentIndex;
        lastSelectedIndex = currentIndex;
        isSelecting = true;
    }

    updateSelectionUI();
}

function handleCardDoubleClick(event, image, card) {
    event.preventDefault();
    openModal(image.path, {
        name: card.querySelector('.formatted-filename').textContent,
        date: card.querySelector('.formatted-date').textContent
    });
}

function clearSelection() {
    document.querySelectorAll('.image-card').forEach(card => {
        card.classList.remove('selected');
    });
    selectedImages.clear();
    lastSelectedIndex = -1;
    selectionStartIndex = -1;
    isSelecting = false;
    updateSelectionUI();
}

function updateSelectionUI() {
    const selectionCount = selectedImages.size;
    const selectionActions = document.getElementById('selectionActions');
    const countElement = document.querySelector('.selection-count');
    
    if (selectionCount > 0) {
        selectionActions.classList.add('active');
        countElement.textContent = `(${selectionCount})`;
    } else {
        selectionActions.classList.remove('active');
        countElement.textContent = '';
    }
}

function handleSortClick(button) {
    document.querySelectorAll('.btn-sort').forEach(btn => {
        btn.classList.remove('active');
    });
    
    button.classList.add('active');
    currentSortCriteria = button.dataset.sort;
    sortAndDisplayImages(false);
}

function handleReverseOrder() {
    isReversed = !isReversed;
    sortAndDisplayImages(false);
}

function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase();
    displayedImages = cachedImages.filter(image => 
        image.name.toLowerCase().includes(searchTerm)
    );
    sortAndDisplayImages(true);
}

function openModal(imagePath, imageData) {
    const modal = document.getElementById('modal');
    const modalImg = document.getElementById('modal-img');
    const modalFilename = document.getElementById('modal-filename');
    const modalDate = document.getElementById('modal-date');
    
    modal.style.display = 'flex';
    modalImg.src = `/output/${imagePath}`;
    modalFilename.textContent = imageData.name;
    modalDate.textContent = imageData.date;
    
    currentImageIndex = parseInt(document.querySelector(`[data-image-path="${imagePath}"]`).dataset.index);
    updateNavButtons();
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

function updateNavButtons() {
    const prevButton = document.querySelector('.prev-button');
    const nextButton = document.querySelector('.next-button');
    
    if (prevButton) prevButton.style.display = currentImageIndex > 0 ? 'flex' : 'none';
    if (nextButton) nextButton.style.display = currentImageIndex < displayedImages.length - 1 ? 'flex' : 'none';
}

function showPrevImage() {
    if (currentImageIndex > 0) {
        currentImageIndex--;
        const prevImage = displayedImages[currentImageIndex];
        const card = document.querySelector(`[data-image-path="${prevImage.path}"]`);
        openModal(prevImage.path, {
            name: card.querySelector('.formatted-filename').textContent,
            date: card.querySelector('.formatted-date').textContent
        });
    }
}

function showNextImage() {
    if (currentImageIndex < displayedImages.length - 1) {
        currentImageIndex++;
        const nextImage = displayedImages[currentImageIndex];
        const card = document.querySelector(`[data-image-path="${nextImage.path}"]`);
        openModal(nextImage.path, {
            name: card.querySelector('.formatted-filename').textContent,
            date: card.querySelector('.formatted-date').textContent
        });
    }
}

document.addEventListener('keydown', function(e) {
    if (document.getElementById('modal').style.display === 'flex') {
        if (e.key === 'ArrowLeft') {
            showPrevImage();
        } else if (e.key === 'ArrowRight') {
            showNextImage();
        } else if (e.key === 'Escape') {
            closeModal();
        }
    }
    
    if (e.ctrlKey && e.altKey && e.key.toLowerCase() === 'd') {
        e.preventDefault(); // Prevent default browser behavior
        
        const currentView = localStorage.getItem('preferredView') || 'image';
        const selectedItems = currentView === 'image' ? selectedImages : selectedTextFiles;
        
        if (selectedItems.size > 0) {
            deleteSelected();
        } else {
            showToast('No items selected');
        }
    }
});

document.addEventListener('click', function(event) {
    const modal = document.getElementById('modal');
    if (event.target === modal) {
        closeModal();
    }
});

// Add these workflow-related functions
async function openWorkflowModal() {
    const modal = document.getElementById('workflowModal');
    modal.style.display = 'flex';
    
    // Load folders first
    await loadWorkflowFolders();
}

async function loadWorkflowFolders() {
    try {
        const response = await fetch('/api/workflow-folders');
        if (!response.ok) throw new Error('Failed to fetch workflow folders');
        
        const folders = await response.json();
        const select = document.getElementById('workflowFolder');
        
        select.innerHTML = folders.map(folder => `
            <option value="${folder.path}">
                ${folder.name} (${folder.count} workflows)
            </option>
        `).join('');
        
        // Load workflows from first folder
        if (folders.length > 0) {
            loadWorkflowsFromFolder(folders[0].path);
        }
        
    } catch (error) {
        console.error('Error loading workflow folders:', error);
        const select = document.getElementById('workflowFolder');
        select.innerHTML = '<option value="">Error loading folders</option>';
    }
}

async function loadWorkflowsFromFolder(folderPath) {
    const list = document.querySelector('.workflow-list');
    list.innerHTML = '<div class="loading">Loading workflows...</div>';
    
    try {
        const response = await fetch('/api/workflows', {
            headers: {
                'X-Workflow-Folder': folderPath
            }
        });
        
        if (!response.ok) throw new Error('Failed to fetch workflows');
        
        const workflows = await response.json();
        list.innerHTML = '';
        
        if (workflows.length === 0) {
            list.innerHTML = '<div class="no-workflows">No workflows found in this folder</div>';
            return;
        }
        
        workflows.forEach(workflow => {
            const item = document.createElement('div');
            item.className = 'workflow-item';
            if (workflow.path === selectedWorkflowPath) {
                item.classList.add('selected');
            }
            
            item.innerHTML = `
                <span class="workflow-icon">📄</span>
                <span class="workflow-name">${workflow.name}</span>
            `;
            
            item.addEventListener('click', () => {
                document.querySelectorAll('.workflow-item').forEach(i => i.classList.remove('selected'));
                item.classList.add('selected');
                selectedWorkflowPath = workflow.path;
                document.getElementById('selectedWorkflowName').textContent = workflow.name;
                document.querySelector('.run-workflow').disabled = false;
                closeWorkflowModal();
            });
            
            list.appendChild(item);
        });
        
    } catch (error) {
        console.error('Error loading workflows:', error);
        list.innerHTML = '<div class="error">Failed to load workflows</div>';
    }
}

async function runSelectedWorkflow() {
    if (!selectedWorkflowPath) {
        showToast('Please select a workflow first');
        return;
    }
    
    const runButton = document.querySelector('.run-workflow');
    const originalText = runButton.innerHTML;
    runButton.innerHTML = '<span class="button-icon"></span>Running...';
    runButton.disabled = true;
    
    try {
        const response = await fetch(`/api/run-workflow/${encodeURIComponent(selectedWorkflowPath)}`);
        const result = await response.json();
        
        if (result.success) {
            showToast('Workflow started successfully');
        } else {
            showToast('Failed to run workflow');
            console.error('Workflow error:', result.error);
        }
    } catch (error) {
        console.error('Error running workflow:', error);
        showToast('Error running workflow');
    } finally {
        runButton.disabled = false;
        runButton.innerHTML = originalText;
    }
}

function closeWorkflowModal() {
    document.getElementById('workflowModal').style.display = 'none';
}

// Add this function to show toast messages
function showToast(message, duration = 3000) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    
    if (!toast || !toastMessage) return;
    
    toastMessage.textContent = message;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

// Add these functions for side panel behavior
function initializeSidePanel() {
    const body = document.body;
    
    // Create trigger area
    const trigger = document.createElement('div');
    trigger.className = 'side-panel-trigger';
    body.appendChild(trigger);
    
    // Add event listeners
    trigger.addEventListener('mouseenter', showPanel);
    const sidePanel = document.querySelector('.side-panel');
    sidePanel.addEventListener('mouseleave', hidePanel);
    
    // Load pinned state from localStorage
    const isPinned = localStorage.getItem('sidePanelPinned') === 'true';
    if (isPinned) {
        sidePanel.classList.add('pinned');
        document.querySelector('.pin-button').classList.add('pinned');
        document.querySelector('.main-content').classList.add('shifted');
    }
}

function showPanel() {
    const sidePanel = document.querySelector('.side-panel');
    const mainContent = document.querySelector('.main-content');
    
    if (!sidePanel.classList.contains('pinned')) {
        sidePanel.classList.add('visible');
        mainContent.classList.add('shifted');
    }
}

function hidePanel() {
    const sidePanel = document.querySelector('.side-panel');
    const mainContent = document.querySelector('.main-content');
    
    if (!sidePanel.classList.contains('pinned')) {
        sidePanel.classList.remove('visible');
        mainContent.classList.remove('shifted');
    }
}

function togglePin() {
    const sidePanel = document.querySelector('.side-panel');
    const pinButton = document.querySelector('.pin-button');
    const mainContent = document.querySelector('.main-content');
    
    if (sidePanel.classList.contains('pinned')) {
        sidePanel.classList.remove('pinned');
        pinButton.classList.remove('pinned');
        localStorage.setItem('sidePanelPinned', 'false');
        hidePanel();
    } else {
        sidePanel.classList.add('pinned');
        pinButton.classList.add('pinned');
        localStorage.setItem('sidePanelPinned', 'true');
    }
}

// Add these functions for the side panel buttons

// Console button handler
function openConsoleModal() {
    const modal = document.getElementById('consoleModal');
    if (!modal) return;
    
    modal.style.display = 'flex';
    
    // Start listening for console updates
    if (!consoleEventSource) {
        consoleEventSource = new EventSource('/api/console');
        consoleEventSource.onmessage = function(event) {
            const consoleOutput = document.getElementById('consoleOutput');
            if (!consoleOutput) return;
            
            const data = JSON.parse(event.data);
            
            const entry = document.createElement('div');
            entry.className = `log-entry ${data.level.toLowerCase()}`;
            entry.textContent = `[${data.time}] ${data.message}`;
            
            consoleOutput.appendChild(entry);
            
            if (autoScroll) {
                consoleOutput.scrollTop = consoleOutput.scrollHeight;
            }
        };
    }
    
    // Add click outside listener
    modal.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeConsoleModal();
        }
    });
}

function closeConsoleModal() {
    const modal = document.getElementById('consoleModal');
    if (!modal) return;
    
    modal.style.display = 'none';
    
    if (consoleEventSource) {
        consoleEventSource.close();
        consoleEventSource = null;
    }
}

function clearConsole() {
    const consoleOutput = document.getElementById('consoleOutput');
    consoleOutput.innerHTML = '';
}

let autoScroll = true;
function toggleAutoScroll() {
    autoScroll = !autoScroll;
    const button = document.getElementById('autoScrollButton');
    button.innerHTML = `<span class="button-icon">📜</span>Auto-scroll: ${autoScroll ? 'ON' : 'OFF'}`;
}

// Test Connection button handler
async function testConnection() {
    const button = document.querySelector('.health-check');
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="button-icon">⌛</span>Testing...';
    button.disabled = true;

    const results = {
        api: false,
        ui: false,
        events: false
    };

    try {
        // Test API response time
        const apiStart = performance.now();
        const apiResponse = await fetch('/api/images');
        const apiEnd = performance.now();
        results.api = {
            status: apiResponse.ok,
            time: Math.round(apiEnd - apiStart)
        };

        // Test UI responsiveness
        const uiStart = performance.now();
        await new Promise(resolve => {
            requestAnimationFrame(() => {
                const uiEnd = performance.now();
                results.ui = {
                    status: true,
                    time: Math.round(uiEnd - uiStart)
                };
                resolve();
            });
        });

        // Test EventSource connection
        results.events = await testEventSource();

        // Show results
        showConnectionResults(results);
    } catch (error) {
        console.error('Connection test error:', error);
        showToast('Connection test failed');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Restart Server button handler
async function restartServer() {
    if (!confirm('Are you sure you want to restart the gallery server?')) {
        return;
    }

    const button = document.querySelector('.restart-button');
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="button-icon">⌛</span>Restarting...';
    button.disabled = true;

    try {
        const response = await fetch('/api/restart');
        if (response.ok) {
            showToast('Server is restarting...');
            
            // Wait a moment before starting reconnection attempts
            setTimeout(async () => {
                let attempts = 0;
                const maxAttempts = 30;
                const checkServer = async () => {
                    try {
                        const response = await fetch('/api/images');
                        if (response.ok) {
                            showToast('Server restarted successfully');
                            window.location.reload();
                            return;
                        }
                    } catch (e) {
                        // Server not ready yet
                    }
                    
                    attempts++;
                    if (attempts < maxAttempts) {
                        setTimeout(checkServer, 1000);
                    } else {
                        showToast('Server restart timed out. Please refresh manually.');
                        button.innerHTML = originalText;
                        button.disabled = false;
                    }
                };
                
                checkServer();
            }, 2000);
            
        } else {
            throw new Error('Failed to restart server');
        }
    } catch (error) {
        console.error('Error restarting server:', error);
        showToast('Failed to restart server');
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Add these helper functions
let consoleEventSource = null;

function testEventSource() {
    return new Promise((resolve) => {
        const start = performance.now();
        const testSource = new EventSource('/events');
        let received = false;

        const timeout = setTimeout(() => {
            testSource.close();
            resolve({
                status: false,
                time: 0
            });
        }, 5000);

        testSource.onopen = () => {
            console.log('EventSource connection opened');
        };

        testSource.onmessage = (event) => {
            console.log('EventSource message received:', event.data);
            if (!received) {
                received = true;
                const end = performance.now();
                clearTimeout(timeout);
                testSource.close();
                resolve({
                    status: true,
                    time: Math.round(end - start)
                });
            }
        };

        testSource.onerror = (error) => {
            console.error('EventSource error:', error);
            clearTimeout(timeout);
            testSource.close();
            resolve({
                status: false,
                time: 0
            });
        };
    });
}

function showConnectionResults(results) {
    const modal = document.createElement('div');
    modal.className = 'modal connection-results-modal';
    
    const content = document.createElement('div');
    content.className = 'modal-content';
    
    content.innerHTML = `
        <button class="close-modal" onclick="this.closest('.modal').remove()">×</button>
        <h3 class="modal-title">Connection Test Results</h3>
        
        <div class="test-results">
            <div class="test-item ${results.api.status ? 'success' : 'failure'}">
                <div class="test-header">
                    <span class="test-icon">${results.api.status ? '✅' : '❌'}</span>
                    <span class="test-name">API Connection</span>
                </div>
                <div class="test-details">
                    Response Time: ${results.api.time}ms
                </div>
            </div>
            
            <div class="test-item ${results.ui.status ? 'success' : 'failure'}">
                <div class="test-header">
                    <span class="test-icon">${results.ui.status ? '✅' : '❌'}</span>
                    <span class="test-name">UI Responsiveness</span>
                </div>
                <div class="test-details">
                    Frame Time: ${results.ui.time}ms
                </div>
            </div>
            
            <div class="test-item ${results.events.status ? 'success' : 'failure'}">
                <div class="test-header">
                    <span class="test-icon">${results.events.status ? '✅' : '❌'}</span>
                    <span class="test-name">Real-time Events</span>
                </div>
                <div class="test-details">
                    ${results.events.status ? `Connection Time: ${results.events.time}ms` : 'Connection Failed'}
                </div>
            </div>
        </div>
    `;
    
    modal.appendChild(content);
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

// Add this function to handle modal clicks
function handleModalClick(event) {
    const modals = [
        { id: 'modal', close: closeModal },
        { id: 'workflowModal', close: closeWorkflowModal },
        { id: 'consoleModal', close: closeConsoleModal },
        { id: 'folderBrowserModal', close: closeFolderBrowser },
        { id: 'newImagesModal', close: closeNewImagesModal },
        { id: 'deleteDialog', close: closeDeleteDialog },
        { id: 'renameDialog', close: closeRenameDialog }
    ];

    modals.forEach(({ id, close }) => {
        const modal = document.getElementById(id);
        if (event.target === modal) {
            close();
        }
    });
}

// Add text file selection handling
let selectedTextFiles = new Set();

function handleTextCardClick(event, textFile, card) {
    const currentIndex = parseInt(card.dataset.index);

    if (event.ctrlKey || event.metaKey) {
        // Multi-select with Ctrl/Cmd
        card.classList.toggle('selected');
        if (card.classList.contains('selected')) {
            selectedTextFiles.add(textFile.path);
        } else {
            selectedTextFiles.delete(textFile.path);
        }
    } else if (event.shiftKey) {
        // Range select with Shift
        const start = Math.min(selectionStartIndex, currentIndex);
        const end = Math.max(selectionStartIndex, currentIndex);

        const cards = Array.from(document.querySelectorAll('.text-card'));
        cards.forEach((c, i) => {
            if (i >= start && i <= end) {
                c.classList.add('selected');
                selectedTextFiles.add(c.dataset.filePath);
            } else {
                c.classList.remove('selected');
                selectedTextFiles.delete(c.dataset.filePath);
            }
        });
    } else {
        // Single select
        clearTextSelection();
        card.classList.add('selected');
        selectedTextFiles.add(textFile.path);
        selectionStartIndex = currentIndex;
    }

    updateSelectionUI();
}

function clearTextSelection() {
    document.querySelectorAll('.text-card').forEach(card => {
        card.classList.remove('selected');
    });
    selectedTextFiles.clear();
    selectionStartIndex = -1;
    updateSelectionUI();
}

// Update the updateSelectionUI function to handle both types
function updateSelectionUI() {
    const currentView = localStorage.getItem('preferredView') || 'image';
    const selectedItems = currentView === 'image' ? selectedImages : selectedTextFiles;
    
    const selectionCount = selectedItems.size;
    const selectionActions = document.getElementById('selectionActions');
    const countElement = document.querySelector('.selection-count');
    
    if (selectionCount > 0) {
        selectionActions.classList.add('active');
        countElement.textContent = `(${selectionCount})`;
    } else {
        selectionActions.classList.remove('active');
        countElement.textContent = '';
    }
}

// Update deletion functions for both images and text files
async function deleteSelected() {
    const currentView = localStorage.getItem('preferredView') || 'image';
    const selectedItems = currentView === 'image' ? selectedImages : selectedTextFiles;
    const apiEndpoint = currentView === 'image' ? 'images' : 'texts';
    
    if (selectedItems.size === 0) return;
    
    const itemType = currentView === 'image' ? 'image' : 'text file';
    const message = selectedItems.size === 1 
        ? `Are you sure you want to delete this ${itemType}?` 
        : `Are you sure you want to delete these ${selectedItems.size} ${itemType}s?`;
    
    if (!confirm(message)) {
        return;
    }

    const deleteButton = document.querySelector('.btn-delete-selected');
    const originalText = deleteButton.innerHTML;
    deleteButton.innerHTML = `<span class="button-icon">⌛</span>Deleting...`;
    deleteButton.disabled = true;

    const failedDeletes = [];
    const successfulDeletes = [];
    
    try {
        // Process deletions
        for (const path of selectedItems) {
            try {
                console.log(`Attempting to delete: ${path}`);
                const response = await fetch(`/api/${apiEndpoint}/${encodeURIComponent(path)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    console.log(`Successfully deleted: ${path}`);
                    successfulDeletes.push(path);
                } else {
                    console.warn(`Failed to delete ${path}, status: ${response.status}`);
                    failedDeletes.push(path);
                }
            } catch (fetchError) {
                console.error(`Network error deleting ${path}:`, fetchError);
                failedDeletes.push(path);
            }
        }

        // Show results
        if (successfulDeletes.length > 0) {
            if (failedDeletes.length > 0) {
                showToast(`Successfully deleted ${successfulDeletes.length} items, ${failedDeletes.length} failed`);
            } else {
                showToast(`Successfully deleted ${successfulDeletes.length} items`);
            }
        } else if (failedDeletes.length > 0) {
            showToast(`Failed to delete ${failedDeletes.length} items`);
        }

    } catch (error) {
        console.error('Unexpected error during deletion process:', error);
        showToast('Unexpected error during deletion');
        return;
    }

    try {
        // Refresh the view
        if (currentView === 'image') {
            await loadImages(true);
        } else {
            await loadTextFiles(true);
        }
    } catch (refreshError) {
        console.error('Error refreshing view:', refreshError);
        // Don't show another toast here as the deletion was successful
    }

    // Clear selection
    selectedItems.clear();
    updateSelectionUI();

    // Reset button state
    deleteButton.innerHTML = originalText;
    deleteButton.disabled = false;
}

// Update the folder browser functions
function openFolderBrowser() {
    const modal = document.getElementById('folderBrowserModal');
    if (!modal) {
        console.error('Folder browser modal not found');
        return;
    }
    
    modal.style.display = 'flex';
    
    // Reset show all checkbox
    const checkbox = document.getElementById('showAllFiles');
    if (checkbox) {
        checkbox.checked = false;
    }
    
    // Start from comfy_dir
    browsePath(null);
}

function closeFolderBrowser() {
    const modal = document.getElementById('folderBrowserModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Update the console button to show options
function showConsoleOptions(event) {
    const button = event.currentTarget;
    const rect = button.getBoundingClientRect();
    
    const menu = document.createElement('div');
    menu.className = 'console-options-menu';
    menu.innerHTML = `
        <div class="menu-item" onclick="openConsoleModal()">
            <span class="menu-icon">🔲</span>
            View in Modal
        </div>
        <div class="menu-item" onclick="openConsoleWindow()">
            <span class="menu-icon">🪟</span>
            Open in New Window
        </div>
    `;
    
    // Position the menu below the button
    menu.style.position = 'absolute';
    menu.style.top = `${rect.bottom + 5}px`;
    menu.style.left = `${rect.left}px`;
    
    // Remove existing menu if any
    const existingMenu = document.querySelector('.console-options-menu');
    if (existingMenu) {
        existingMenu.remove();
    }
    
    document.body.appendChild(menu);
    
    // Close menu when clicking outside
    const closeMenu = (e) => {
        if (!menu.contains(e.target) && e.target !== button) {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        }
    };
    document.addEventListener('click', closeMenu);
}

// Add function to open console in new window
let consoleWindow = null;
function openConsoleWindow() {
    // Close modal if open
    closeConsoleModal();
    
    // Close existing window if open
    if (consoleWindow && !consoleWindow.closed) {
        consoleWindow.focus();
        return;
    }
    
    // Open new window
    consoleWindow = window.open('', 'ComfyUI Console', 'width=800,height=600');
    
    // Add the content with proper event handling
    consoleWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>ComfyUI Console</title>
            <style>
                body {
                    margin: 0;
                    padding: 20px;
                    background: #282a36;
                    color: #f8f8f2;
                    font-family: 'Consolas', 'Monaco', monospace;
                }
                .console-container {
                    height: calc(100vh - 100px);
                    background: rgba(0, 0, 0, 0.3);
                    border: 2px solid #6272a4;
                    border-radius: 8px;
                    padding: 10px;
                    overflow-y: auto;
                }
                .console-output {
                    padding: 10px;
                    white-space: pre-wrap;
                    font-size: 0.9em;
                    line-height: 1.4;
                }
                .log-entry {
                    margin: 2px 0;
                    padding: 2px 5px;
                    border-radius: 4px;
                    animation: fadeIn 0.3s ease;
                }
                .info { color: #50fa7b; }
                .error { 
                    color: #ff5555;
                    background: rgba(255, 85, 85, 0.1);
                }
                .warning {
                    color: #ffb86c;
                    background: rgba(255, 184, 108, 0.1);
                }
                .controls {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    display: flex;
                    gap: 10px;
                }
                .control-button {
                    background: rgba(98, 114, 164, 0.2);
                    border: 2px solid #6272a4;
                    color: #6272a4;
                    padding: 8px 15px;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                }
                .control-button:hover {
                    background: rgba(98, 114, 164, 0.3);
                    color: #f8f8f2;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-5px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            </style>
        </head>
        <body>
            <div class="console-container">
                <div id="consoleOutput" class="console-output"></div>
            </div>
            <div class="controls">
                <button class="control-button" onclick="clearConsole()">Clear</button>
                <button class="control-button" id="autoScrollButton" onclick="toggleAutoScroll()">
                    Auto-scroll: ON
                </button>
            </div>
            <script>
                let autoScroll = true;
                let consoleEventSource = null;
                
                function clearConsole() {
                    document.getElementById('consoleOutput').innerHTML = '';
                }
                
                function toggleAutoScroll() {
                    autoScroll = !autoScroll;
                    const button = document.getElementById('autoScrollButton');
                    button.textContent = 'Auto-scroll: ' + (autoScroll ? 'ON' : 'OFF');
                }
                
                function initConsole() {
                    // Setup EventSource for console updates
                    consoleEventSource = new EventSource('/api/console');
                    
                    consoleEventSource.onopen = function() {
                        console.log('Console connection opened');
                    };
                    
                    consoleEventSource.onmessage = function(event) {
                        const consoleOutput = document.getElementById('consoleOutput');
                        try {
                            const data = JSON.parse(event.data);
                            
                            const entry = document.createElement('div');
                            entry.className = 'log-entry ' + data.level.toLowerCase();
                            entry.textContent = '[' + data.time + '] ' + data.message;
                            
                            consoleOutput.appendChild(entry);
                            
                            if (autoScroll) {
                                consoleOutput.scrollTop = consoleOutput.scrollHeight;
                            }
                        } catch (error) {
                            console.error('Error processing console message:', error);
                        }
                    };
                    
                    consoleEventSource.onerror = function(error) {
                        console.error('Console connection error:', error);
                        // Try to reconnect after a delay
                        setTimeout(initConsole, 5000);
                    };
                }
                
                // Initialize console when window loads
                window.onload = initConsole;
                
                // Clean up when window closes
                window.onbeforeunload = function() {
                    if (consoleEventSource) {
                        consoleEventSource.close();
                        consoleEventSource = null;
                    }
                };
            </script>
        </body>
        </html>
    `);
    
    // Close the document after writing
    consoleWindow.document.close();
}

// Add these folder browsing functions
async function browsePath(path) {
    const currentPathElement = document.getElementById('currentPath');
    const folderList = document.querySelector('.folder-list');
    const selectButton = document.getElementById('selectFolderButton');
    const showAllFiles = document.getElementById('showAllFiles').checked;
    
    try {
        // Show loading state
        folderList.innerHTML = '<div class="loading">Loading...</div>';
        
        const response = await fetch('/api/browse-folders', {
            headers: {
                'X-Current-Path': path || '',
                'X-Show-All': showAllFiles.toString()
            }
        });
        
        if (!response.ok) throw new Error('Failed to load folders');
        
        const data = await response.json();
        currentPathElement.textContent = data.current_path;
        
        // Clear and populate folder list
        folderList.innerHTML = '';
        
        data.items.forEach(item => {
            const itemElement = document.createElement('div');
            itemElement.className = `folder-item${item.is_file ? ' file' : ''}`;
            
            // Determine icon based on item type
            let icon = item.is_file ? '📄' : (item.name === '..' ? '⬆️' : '📁');
            
            itemElement.innerHTML = `
                <span class="item-icon">${icon}</span>
                <span class="item-name">${item.name}</span>
                ${item.has_json ? '<span class="item-badge">JSON</span>' : ''}
            `;
            
            itemElement.addEventListener('click', () => {
                if (item.is_file) {
                    if (item.is_json) {
                        selectWorkflowFile(item.path);
                    }
                } else {
                    browsePath(item.path);
                }
            });
            
            folderList.appendChild(itemElement);
        });
        
        // Enable/disable select button based on JSON files presence
        const hasJsonFiles = data.items.some(item => item.has_json);
        selectButton.disabled = !hasJsonFiles;
        
    } catch (error) {
        console.error('Error browsing folders:', error);
        folderList.innerHTML = '<div class="error">Failed to load folder contents</div>';
        selectButton.disabled = true;
    }
}

function selectWorkflowFile(path) {
    // Update workflow folder select
    const folderSelect = document.getElementById('workflowFolder');
    const folderPath = path.substring(0, path.lastIndexOf('/'));
    
    // Find or add the folder option
    let option = Array.from(folderSelect.options).find(opt => opt.value === folderPath);
    if (!option) {
        option = new Option(folderPath, folderPath);
        folderSelect.add(option);
    }
    
    // Select the folder
    folderSelect.value = folderPath;
    
    // Load workflows from this folder
    loadWorkflowsFromFolder(folderPath);
    
    // Close the browser
    closeFolderBrowser();
}

function selectCurrentFolder() {
    const currentPath = document.getElementById('currentPath').textContent;
    const folderSelect = document.getElementById('workflowFolder');
    
    // Find or add the folder option
    let option = Array.from(folderSelect.options).find(opt => opt.value === currentPath);
    if (!option) {
        option = new Option(currentPath, currentPath);
        folderSelect.add(option);
    }
    
    // Select the folder
    folderSelect.value = currentPath;
    
    // Load workflows from this folder
    loadWorkflowsFromFolder(currentPath);
    
    // Close the browser
    closeFolderBrowser();
}

function refreshBrowser() {
    const currentPath = document.getElementById('currentPath').textContent;
    browsePath(currentPath);
}