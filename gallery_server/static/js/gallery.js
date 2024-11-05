// State management
let cachedImages = [];
let displayedImages = [];
let selectedImages = new Set();
let lastSelectedIndex = -1;
let currentImageIndex = 0;
let lastUpdateTime = 0;
let isReversed = false;
let currentSortCriteria = 'date-desc';
let serverConnected = true;
let preventSingleClick = false;
let clickTimer = null;
let selectionStartIndex = -1;  // Track the start of the current selection
let isSelecting = false;      // Track if we're in a selection process
let newImages = new Set();
let lastImageCount = 0;

// Constants
const UPDATE_INTERVAL = 10000;
const DOUBLE_CLICK_DELAY = 300;
const STORAGE_KEY = 'gallery_images';
const STORAGE_VERSION = '1.0';  // Increment this when storage format changes
const MAX_CACHE_AGE = 1000 * 60 * 60 * 24;  // 24 hours in milliseconds

// Sort functions
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

// Image handling functions
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
                <div class="click-layer"></div>
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
    const container = card.querySelector('.image-container');
    container.addEventListener('click', (event) => handleCardClick(event, image, card));
    container.addEventListener('dblclick', (event) => handleCardDoubleClick(event, image, card));

    // Add context menu event
    container.addEventListener('contextmenu', (event) => showContextMenu(event, image, card));

    return card;
}

// Click handlers
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
    // Open modal on double click
    openModal(image.path, {
        name: card.querySelector('.formatted-filename').textContent,
        date: card.querySelector('.formatted-date').textContent
    });
}

// Modal functions
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

    // Add escape key handler
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

// Navigation functions
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

// Sort and display functions
function handleSortClick(button) {
    document.querySelectorAll('.btn-sort').forEach(btn => {
        btn.classList.remove('active');
    });
    
    button.classList.add('active');
    currentSortCriteria = button.dataset.sort;
    sortAndDisplayImages(false);
    localStorage.setItem('imageSortCriteria', currentSortCriteria);
}

function handleReverseOrder() {
    isReversed = !isReversed;
    sortAndDisplayImages(false);
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
    } else {
        const fragment = document.createDocumentFragment();
        imagesToSort.forEach((image, index) => {
            const existingCard = gallery.querySelector(`[data-image-path="${image.path}"]`);
            if (existingCard) {
                existingCard.dataset.index = index;
                fragment.appendChild(existingCard);
            } else {
                const card = createImageCard(image, index);
                fragment.appendChild(card);
            }
        });
        gallery.innerHTML = '';
        gallery.appendChild(fragment);
    }

    displayedImages = imagesToSort;
}

// Search function
function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase();
    displayedImages = cachedImages.filter(image => 
        image.name.toLowerCase().includes(searchTerm)
    );
    sortAndDisplayImages(true);
}

// Image loading and updates
async function loadImages(force = false) {
    const now = Date.now();
    if (!force && now - lastUpdateTime < UPDATE_INTERVAL) {
        return;
    }

    try {
        const response = await fetch('/api/images');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const fetchedImages = await response.json();
        
        if (force || imagesHaveChanged(cachedImages, fetchedImages)) {
            // Find new images
            const newImagesList = fetchedImages.filter(img => 
                !cachedImages.some(cached => cached.path === img.path)
            );
            
            if (newImagesList.length > 0) {
                showNewImagesModal(newImagesList);
            }
            
            cachedImages = fetchedImages;
            
            if (!document.getElementById('searchInput').value) {
                displayedImages = [...fetchedImages];
                await sortAndDisplayImages(true);
            }
            
            lastUpdateTime = now;
            updateServerStatus(true);
            
            // Save to localStorage after successful update
            saveToLocalStorage();
        }
    } catch (error) {
        console.error('Error loading images:', error);
        updateServerStatus(false);
        
        // Try to load from localStorage if server request fails
        if (cachedImages.length === 0) {
            loadFromLocalStorage();
        }
    }
}

// Utility functions
function formatFilename(filename) {
    return filename
        .replace(/\.[^/.]+$/, '')
        .replace(/_/g, ' ')
        .replace(/(\d+)$/, ' #$1')
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

function imagesHaveChanged(oldImages, newImages) {
    if (oldImages.length !== newImages.length) return true;
    
    const oldMap = new Map(oldImages.map(img => [img.path, img]));
    const newMap = new Map(newImages.map(img => [img.path, img]));
    
    for (const [path, oldImg] of oldMap) {
        const newImg = newMap.get(path);
        if (!newImg || oldImg.date !== newImg.date) return true;
    }
    
    return false;
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

// Add these functions for storage management
function saveToLocalStorage() {
    const storageData = {
        version: STORAGE_VERSION,
        timestamp: Date.now(),
        images: cachedImages,
        lastUpdateTime: lastUpdateTime
    };
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(storageData));
    } catch (e) {
        console.warn('Failed to save to localStorage:', e);
    }
}

function loadFromLocalStorage() {
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        if (!data) return false;

        const storageData = JSON.parse(data);
        
        // Check version and age
        if (storageData.version !== STORAGE_VERSION) {
            console.log('Cache version mismatch, clearing storage');
            localStorage.removeItem(STORAGE_KEY);
            return false;
        }

        if (Date.now() - storageData.timestamp > MAX_CACHE_AGE) {
            console.log('Cache too old, clearing storage');
            localStorage.removeItem(STORAGE_KEY);
            return false;
        }

        // Restore data
        cachedImages = storageData.images;
        displayedImages = [...cachedImages];
        lastUpdateTime = storageData.lastUpdateTime;
        
        // Display cached images immediately
        sortAndDisplayImages(true);
        return true;
    } catch (e) {
        console.warn('Failed to load from localStorage:', e);
        return false;
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    currentSortCriteria = localStorage.getItem('imageSortCriteria') || 'date-desc';
    
    const activeButton = document.querySelector(`[data-sort="${currentSortCriteria}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }

    // Try to load cached images first
    const hasCachedData = loadFromLocalStorage();
    
    // Always fetch fresh data, but display cached data immediately if available
    await loadImages(!hasCachedData);
    
    // Start periodic refresh
    setInterval(() => {
        if (document.visibilityState === 'visible') {
            loadImages();
        }
    }, UPDATE_INTERVAL);
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    if (e.key === 'a' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        const allCards = document.querySelectorAll('.image-card');
        if (selectedImages.size === allCards.length) {
            clearSelection();
        } else {
            allCards.forEach(card => {
                card.classList.add('selected');
                selectedImages.add(card.dataset.imagePath);
            });
        }
        updateSelectionUI();
    } else if (e.key === 'Escape') {
        clearSelection();
        closeModal();
    }
});

// Add this function to clear selection
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

// Add this function to update selection UI
function updateSelectionUI() {
    const selectionCount = selectedImages.size;
    const selectionActions = document.getElementById('selectionActions');
    const countElement = document.querySelector('.selection-count');
    
    if (selectionCount > 0) {
        selectionActions.classList.add('active');
        countElement.textContent = `(${selectionCount})`;
        
        if (selectionStartIndex === -1) {
            selectionStartIndex = getFirstSelectedIndex();
            isSelecting = true;
        }
    } else {
        selectionActions.classList.remove('active');
        countElement.textContent = '';
        selectionStartIndex = -1;
        isSelecting = false;
    }

    // Update delete button state
    const deleteButton = document.querySelector('.btn-delete-selected');
    if (deleteButton) {
        deleteButton.disabled = selectionCount === 0;
        deleteButton.title = selectionCount === 0 ? 'Select images to delete' : `Delete ${selectionCount} selected image${selectionCount > 1 ? 's' : ''}`;
    }
}

// Add click handler to clear selection when clicking outside
document.addEventListener('click', function(event) {
    if (!event.target.closest('.image-card') && 
        !event.target.closest('.selection-actions') &&
        !event.ctrlKey && !event.metaKey && !event.shiftKey) {
        clearSelection();
    }
});

// Add function to check if any images are selected
function hasSelectedImages() {
    return selectedImages.size > 0;
}

// Add function to get first selected image index
function getFirstSelectedIndex() {
    const selectedCard = document.querySelector('.image-card.selected');
    return selectedCard ? parseInt(selectedCard.dataset.index) : -1;
}

// Add these functions for handling multiple deletions

async function deleteSelected() {
    if (selectedImages.size === 0) return;

    const count = selectedImages.size;
    if (confirm(`Are you sure you want to delete ${count} selected image${count > 1 ? 's' : ''}? This action cannot be undone.`)) {
        const deletePromises = Array.from(selectedImages).map(imagePath => 
            fetch(`/api/images/${imagePath}`, {
                method: 'DELETE'
            }).then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to delete ${imagePath}`);
                }
                return imagePath;
            })
        );

        try {
            const results = await Promise.allSettled(deletePromises);
            
            // Count successful and failed deletions
            const successful = results.filter(r => r.status === 'fulfilled').length;
            const failed = results.filter(r => r.status === 'rejected').length;
            
            // Show results
            if (failed === 0) {
                showToast(`Successfully deleted ${successful} image${successful > 1 ? 's' : ''}`);
            } else {
                showToast(`Deleted ${successful} image${successful > 1 ? 's' : ''}, ${failed} failed`);
            }

            // Clear selection
            clearSelection();
            
            // Refresh the gallery
            await loadImages(true);
        } catch (error) {
            console.error('Error during batch deletion:', error);
            showToast('Error deleting selected images');
        }
    }
}

// Add toast notification function
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

// Add these functions for context menu handling
let contextMenuTarget = null;

function showContextMenu(event, image, card) {
    event.preventDefault();
    const contextMenu = document.getElementById('contextMenu');
    contextMenuTarget = { image, card };
    
    // Position the menu
    contextMenu.style.display = 'block';
    const x = event.clientX;
    const y = event.clientY;
    
    // Adjust position if menu would go off screen
    const menuRect = contextMenu.getBoundingClientRect();
    const adjustedX = x + menuRect.width > window.innerWidth ? x - menuRect.width : x;
    const adjustedY = y + menuRect.height > window.innerHeight ? y - menuRect.height : y;
    
    contextMenu.style.left = `${adjustedX}px`;
    contextMenu.style.top = `${adjustedY}px`;
}

// Add rename functionality
function openRenameDialog() {
    if (!contextMenuTarget) return;
    
    const dialog = document.getElementById('renameDialog');
    const input = document.getElementById('newFilename');
    const currentName = contextMenuTarget.image.name.replace(/\.[^/.]+$/, '');
    
    input.value = currentName;
    dialog.style.display = 'block';
    input.select();

    // Add escape key handler
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            closeRenameDialog();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

async function confirmRename() {
    if (!contextMenuTarget) return;
    
    const newName = document.getElementById('newFilename').value;
    const ext = contextMenuTarget.image.name.split('.').pop();
    const fullNewName = `${newName}.${ext}`;
    
    try {
        const response = await fetch(`/api/rename/${contextMenuTarget.image.path}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ newName: fullNewName })
        });
        
        if (response.ok) {
            showToast(`Renamed to ${fullNewName}`);
            await loadImages(true);
        } else {
            showToast('Failed to rename file');
        }
    } catch (error) {
        console.error('Error renaming file:', error);
        showToast('Error renaming file');
    }
    
    closeRenameDialog();
}

function closeRenameDialog() {
    document.getElementById('renameDialog').style.display = 'none';
    contextMenuTarget = null;
}

// Add click handler to close context menu when clicking outside
document.addEventListener('click', function(event) {
    const contextMenu = document.getElementById('contextMenu');
    if (!event.target.closest('.context-menu')) {
        contextMenu.style.display = 'none';
        contextMenuTarget = null;
    }
});

// Add these functions to handle the new images modal
function showNewImagesModal(newImagesList) {
    const modal = document.getElementById('newImagesModal');
    const grid = modal.querySelector('.new-images-grid');
    grid.innerHTML = '';
    
    newImagesList.forEach(image => {
        const card = createNewImageCard(image);
        grid.appendChild(card);
        newImages.add(image.path);
    });
    
    modal.style.display = 'flex';
    showToast(`${newImagesList.length} new image${newImagesList.length > 1 ? 's' : ''} added`);

    // Add escape key handler
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            closeNewImagesModal();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

function createNewImageCard(image) {
    const card = document.createElement('div');
    card.className = 'new-image-card';
    card.dataset.imagePath = image.path;
    
    card.innerHTML = `
        <img src="${image.thumbnail || `/output/${image.path}`}" alt="${image.name}">
        <div class="image-info">
            <div class="formatted-filename">${formatFilename(image.name)}</div>
            <div class="formatted-date">${formatDate(image.date)}</div>
        </div>
    `;
    
    card.addEventListener('click', () => {
        card.classList.toggle('selected');
    });
    
    return card;
}

function closeNewImagesModal() {
    document.getElementById('newImagesModal').style.display = 'none';
    newImages.clear();
}

function selectAllNew() {
    const cards = document.querySelectorAll('.new-image-card');
    cards.forEach(card => card.classList.add('selected'));
}

async function downloadAllNew() {
    const selectedCards = document.querySelectorAll('.new-image-card.selected');
    for (const card of selectedCards) {
        const link = document.createElement('a');
        link.href = `/output/${card.dataset.imagePath}`;
        link.download = card.querySelector('.formatted-filename').textContent;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        await new Promise(resolve => setTimeout(resolve, 100)); // Delay between downloads
    }
}

async function deleteAllNew() {
    const selectedCards = document.querySelectorAll('.new-image-card.selected');
    if (selectedCards.length === 0) return;
    
    if (confirm(`Delete ${selectedCards.length} selected image${selectedCards.length > 1 ? 's' : ''}?`)) {
        for (const card of selectedCards) {
            try {
                const response = await fetch(`/api/images/${card.dataset.imagePath}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    card.remove();
                    newImages.delete(card.dataset.imagePath);
                }
            } catch (error) {
                console.error('Error deleting image:', error);
            }
        }
        
        await loadImages(true);
        
        if (document.querySelector('.new-images-grid').children.length === 0) {
            closeNewImagesModal();
        }
    }
}

// Add cleanup function for old cache entries
function cleanupOldCacheEntries() {
    try {
        const keys = Object.keys(localStorage);
        const now = Date.now();
        
        keys.forEach(key => {
            if (key.startsWith(STORAGE_KEY)) {
                try {
                    const data = JSON.parse(localStorage.getItem(key));
                    if (now - data.timestamp > MAX_CACHE_AGE) {
                        localStorage.removeItem(key);
                    }
                } catch (e) {
                    // If the data is invalid, remove it
                    localStorage.removeItem(key);
                }
            }
        });
    } catch (e) {
        console.warn('Error cleaning up cache:', e);
    }
}

// Add periodic cache cleanup
setInterval(cleanupOldCacheEntries, 1000 * 60 * 60); // Check every hour

// Add these functions for modal handling
function handleModalClick(event) {
    const modals = [
        { element: document.getElementById('modal'), close: closeModal },
        { element: document.getElementById('newImagesModal'), close: closeNewImagesModal },
        { element: document.getElementById('renameDialog'), close: closeRenameDialog },
        { element: document.getElementById('consoleModal'), close: closeConsoleModal },
        { element: document.getElementById('folderBrowserModal'), close: closeFolderBrowser }
    ];

    modals.forEach(({ element, close }) => {
        if (event.target === element) {
            close();
        }
    });
}

// Update the modal initialization
document.addEventListener('DOMContentLoaded', function() {
    // ... existing initialization code ...

    // Add click handlers to all modals
    const modals = [
        document.getElementById('modal'),
        document.getElementById('newImagesModal'),
        document.getElementById('renameDialog'),
        document.getElementById('consoleModal'),
        document.getElementById('folderBrowserModal')
    ];

    modals.forEach(modal => {
        if (modal) {
            modal.addEventListener('click', handleModalClick);
        }
    });

    // Prevent clicks inside modal content from closing the modal
    const modalContents = document.querySelectorAll('.modal-content, .dialog-content');
    modalContents.forEach(content => {
        content.addEventListener('click', (e) => e.stopPropagation());
    });
});

// Update the workflow handling functions
let selectedWorkflowPath = null;

async function openWorkflowModal() {
    const modal = document.getElementById('workflowModal');
    const list = modal.querySelector('.workflow-list');
    list.innerHTML = '<div class="loading">Loading workflows...</div>';
    modal.style.display = 'flex';
    
    try {
        const response = await fetch('/api/workflows');
        if (!response.ok) throw new Error('Failed to fetch workflows');
        
        const workflows = await response.json();
        list.innerHTML = '';
        
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
    runButton.innerHTML = '<span class="button-icon">⌛</span>Running...';
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

// Add mobile menu toggle functionality
function toggleSidePanel() {
    const sidePanel = document.querySelector('.side-panel');
    sidePanel.classList.toggle('open');
}

// Add mobile menu button to DOM when viewport is small
function addMobileMenuButton() {
    if (window.innerWidth <= 576 && !document.querySelector('.menu-toggle')) {
        const menuButton = document.createElement('button');
        menuButton.className = 'menu-toggle';
        menuButton.innerHTML = '☰';
        menuButton.onclick = toggleSidePanel;
        document.body.appendChild(menuButton);
    }
}

// Listen for window resize
window.addEventListener('resize', addMobileMenuButton);
// Initial check
document.addEventListener('DOMContentLoaded', addMobileMenuButton);

// Add these functions for side panel behavior
function initializeSidePanel() {
    const body = document.body;
    
    // Create trigger area
    const trigger = document.createElement('div');
    trigger.className = 'side-panel-trigger';
    body.appendChild(trigger);
    
    // Create pin button
    const sidePanel = document.querySelector('.side-panel');
    const pinButton = document.createElement('button');
    pinButton.className = 'pin-button';
    pinButton.innerHTML = '📌';
    pinButton.title = 'Pin panel';
    sidePanel.appendChild(pinButton);
    
    // Add event listeners
    trigger.addEventListener('mouseenter', showPanel);
    sidePanel.addEventListener('mouseleave', hidePanel);
    pinButton.addEventListener('click', togglePin);
    
    // Load pinned state from localStorage
    const isPinned = localStorage.getItem('sidePanelPinned') === 'true';
    if (isPinned) {
        sidePanel.classList.add('visible', 'pinned');
        pinButton.classList.add('pinned');
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

// Update the DOMContentLoaded event listener
document.addEventListener('DOMContentLoaded', function() {
    // Existing initialization code...
    
    // Initialize side panel
    initializeSidePanel();
});

// Add this function near the other server-related functions
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

// Add these console-related functions
let autoScroll = true;
let consoleEventSource = null;

function openConsoleModal() {
    const modal = document.getElementById('consoleModal');
    modal.style.display = 'flex';
    
    // Start listening for console updates
    if (!consoleEventSource) {
        consoleEventSource = new EventSource('/api/console');
        consoleEventSource.onmessage = function(event) {
            const consoleOutput = document.getElementById('consoleOutput');
            const data = JSON.parse(event.data);
            
            // Create new log entry
            const entry = document.createElement('div');
            entry.className = `log-entry ${data.level.toLowerCase()}`;
            entry.textContent = `[${data.time}] ${data.message}`;
            
            consoleOutput.appendChild(entry);
            
            // Auto-scroll if enabled
            if (autoScroll) {
                consoleOutput.scrollTop = consoleOutput.scrollHeight;
            }
        };
    }
}

function closeConsoleModal() {
    const modal = document.getElementById('consoleModal');
    modal.style.display = 'none';
    
    // Close EventSource connection
    if (consoleEventSource) {
        consoleEventSource.close();
        consoleEventSource = null;
    }
}

function clearConsole() {
    const consoleOutput = document.getElementById('consoleOutput');
    consoleOutput.innerHTML = '';
}

function toggleAutoScroll() {
    autoScroll = !autoScroll;
    const button = document.getElementById('autoScrollButton');
    button.innerHTML = `<span class="button-icon">📜</span>Auto-scroll: ${autoScroll ? 'ON' : 'OFF'}`;
}

// Add these functions for folder handling
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

// Update the openWorkflowModal function
async function openWorkflowModal() {
    const modal = document.getElementById('workflowModal');
    modal.style.display = 'flex';
    
    // Load folders first
    await loadWorkflowFolders();
}

// Add these folder browser functions
let currentBrowsePath = null;
let showAllFiles = false;

async function openFolderBrowser() {
    const modal = document.getElementById('folderBrowserModal');
    modal.style.display = 'flex';
    
    // Reset show all checkbox
    document.getElementById('showAllFiles').checked = showAllFiles;
    
    // Start from comfy_dir
    await browsePath(null);
}

async function browsePath(path) {
    const folderList = document.querySelector('.folder-list');
    folderList.innerHTML = '<div class="loading">Loading folders...</div>';
    
    try {
        const headers = {
            'X-Show-All': showAllFiles.toString()
        };
        if (path) {
            headers['X-Current-Path'] = path;
        }
        
        const response = await fetch('/api/browse-folders', { headers });
        if (!response.ok) throw new Error('Failed to browse folders');
        
        const data = await response.json();
        currentBrowsePath = data.current_path;
        
        // Update current path display
        document.getElementById('currentPath').textContent = data.current_path;
        
        // Update select button state - enable if current folder has JSON files
        document.getElementById('selectFolderButton').disabled = !data.items.some(item => 
            !item.is_file && item.has_json && item.name !== '..'
        );
        
        // Populate folder list
        folderList.innerHTML = '';
        data.items.forEach(item => {
            const element = document.createElement('div');
            element.className = `folder-item${item.is_file ? ' file' : ''}`;
            
            let icon, badge = '';
            if (item.name === '..') {
                icon = '⬆️';
            } else if (item.is_file) {
                icon = item.is_json ? '📄' : '📝';
                badge = `<span class="item-badge file-badge">${item.is_json ? 'JSON' : 'File'}</span>`;
            } else {
                icon = '📁';
                if (item.has_json) {
                    badge = '<span class="item-badge">Contains JSON</span>';
                }
            }
            
            element.innerHTML = `
                <span class="item-icon">${icon}</span>
                <span class="item-name">${item.name}</span>
                ${badge}
            `;
            
            if (!item.is_file || item.is_json) {
                element.addEventListener('click', () => browsePath(item.path));
            }
            
            folderList.appendChild(element);
        });
        
    } catch (error) {
        console.error('Error browsing folders:', error);
        folderList.innerHTML = '<div class="error">Failed to load folders</div>';
    }
}

function refreshBrowser() {
    showAllFiles = document.getElementById('showAllFiles').checked;
    browsePath(currentBrowsePath);
}

function closeFolderBrowser() {
    document.getElementById('folderBrowserModal').style.display = 'none';
    currentBrowsePath = null;
}

function selectCurrentFolder() {
    if (!currentBrowsePath) return;
    
    // Add the folder to the dropdown
    const select = document.getElementById('workflowFolder');
    const option = document.createElement('option');
    option.value = currentBrowsePath;
    option.textContent = `Custom: ${currentBrowsePath}`;
    select.appendChild(option);
    select.value = currentBrowsePath;
    
    // Load workflows from the selected folder
    loadWorkflowsFromFolder(currentBrowsePath);
    
    // Close the browser
    closeFolderBrowser();
}