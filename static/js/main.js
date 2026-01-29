document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    const tweetText = document.getElementById('tweetText');
    const mediaInput = document.getElementById('mediaInput');
    const mediaPreview = document.getElementById('mediaPreview');
    const previewImg = document.getElementById('previewImg');
    const removeMedia = document.getElementById('removeMedia');
    const scheduleBtn = document.getElementById('scheduleBtn');
    const scheduleModal = document.getElementById('scheduleModal');
    const closeScheduleModal = document.getElementById('closeScheduleModal');
    const scheduleTime = document.getElementById('scheduleTime');
    const nyTimeDisplay = document.getElementById('nyTimeDisplay');
    const confirmScheduleBtn = document.getElementById('confirmScheduleBtn');
    const clearScheduleBtn = document.getElementById('clearScheduleBtn');
    const postBtn = document.getElementById('postBtn');
    const charCount = document.getElementById('charCount');
    const toast = document.getElementById('toast');

    // History Elements
    const historyList = document.getElementById('historyList');
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');

    // Settings Elements
    const autoPostToggle = document.getElementById('autoPostToggle');

    let confirmedScheduleTime = null;

    // --- Theme Switcher ---
    // ... (existing code) ...

    // --- Initial Load ---
    loadHistory();
    loadSettings();

    refreshHistoryBtn.addEventListener('click', () => {
        refreshHistoryBtn.classList.add('fa-spin');
        loadHistory().finally(() => {
            setTimeout(() => refreshHistoryBtn.classList.remove('fa-spin'), 500);
        });
    });

    // --- Settings Logic ---
    async function loadSettings() {
        try {
            const response = await fetch('/api/settings');
            const result = await response.json();
            if (result.success) {
                autoPostToggle.checked = result.data.enable_auto_post;
            }
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    autoPostToggle.addEventListener('change', async () => {
        const enabled = autoPostToggle.checked;
        try {
            const response = await fetch('/api/settings/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    enable_auto_post: enabled
                })
            });
            const result = await response.json();
            if (result.success) {
                showToast(result.message || 'Settings saved', false);
            } else {
                showToast(result.message || 'Failed to save settings', true);
                // Revert toggle if failed
                autoPostToggle.checked = !enabled;
            }
        } catch (error) {
            console.error('Error updating settings:', error);
            showToast('Network error', true);
            autoPostToggle.checked = !enabled;
        }
    });

    // --- History Logic ---
    async function loadHistory() {
        try {
            const response = await fetch('/api/history');
            const result = await response.json();

            if (result.success) {
                renderHistory(result.data);
            } else {
                historyList.innerHTML = '<div class="loading-spinner">Failed to load history</div>';
            }
        } catch (error) {
            console.error('Error loading history:', error);
            historyList.innerHTML = '<div class="loading-spinner">Network error</div>';
        }
    }

    function renderHistory(items) {
        if (!items || items.length === 0) {
            historyList.innerHTML = '<div class="loading-spinner">No history yet</div>';
            return;
        }

        historyList.innerHTML = items.map(item => {
            let statusClass = '';
            let statusIcon = '';
            let actions = '';

            switch (item.status) {
                case 'pending':
                    statusClass = 'status-pending';
                    statusIcon = '⏳ Pending';
                    actions = `<button class="btn-sm btn-outline-danger" onclick="cancelJob('${item.id}')">Cancel</button>`;
                    break;
                case 'sent':
                    statusClass = 'status-sent';
                    statusIcon = '✅ Sent';
                    if (item.tweet_url) {
                        actions = `<a href="${item.tweet_url}" target="_blank" class="btn-sm btn-outline-primary">View <i class="fas fa-external-link-alt"></i></a>`;
                    }
                    break;
                case 'failed':
                    statusClass = 'status-failed';
                    statusIcon = '❌ Failed';
                    break;
                case 'cancelled':
                    statusClass = 'status-cancelled';
                    statusIcon = '🚫 Cancelled';
                    break;
                default:
                    statusClass = 'status-cancelled';
                    statusIcon = item.status;
            }

            // Format time (Force Beijing Time)
            const date = new Date(item.created_at);
            const timeStr = date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });

            let scheduledInfo = '';
            if (item.scheduled_time && item.status === 'pending') {
                const scheduledDate = new Date(item.scheduled_time);
                const scheduledStr = scheduledDate.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });
                scheduledInfo = `<div style="font-size: 12px; color: var(--primary-color); margin-top: 4px;">Scheduled for: ${scheduledStr} (Beijing Time)</div>`;
            }

            let mediaPreview = '';
            if (item.media_urls && item.media_urls.length > 0) {
                mediaPreview = `<div class="history-media-preview" style="display: flex; gap: 8px; margin-top: 8px;">
                    ${item.media_urls.map(url => `<img src="${url}" style="width: 60px; height: 60px; object-fit: cover; border-radius: 8px; border: 1px solid var(--border-color);">`).join('')}
                </div>`;
            }

            return `
                <div class="history-item">
                    <div class="history-item-header">
                        <div>
                            <span class="status-badge ${statusClass}">${statusIcon}</span>
                            ${item.source ? `<span class="status-badge" style="background: ${item.source === 'auto' ? '#1d9bf0' : '#71767b'}; color: white;">${item.source === 'auto' ? 'Auto' : 'Manual'}</span>` : ''}
                            ${item.mode ? `<span class="status-badge" style="background: ${item.mode === 'test' ? '#f4ae41' : '#00ba7c'}; color: white;">${item.mode === 'test' ? 'Test' : 'Live'}</span>` : ''}
                        </div>
                        <span class="history-time">${timeStr}</span>
                    </div>
                    <div class="history-content">
                        ${escapeHtml(item.content || '')}
                    </div>
                    ${mediaPreview}
                    ${scheduledInfo}
                    ${item.error ? `<div style="font-size: 12px; color: #f4212e;">Error: ${item.error}</div>` : ''}
                    <div class="history-actions">
                        ${actions}
                    </div>
                </div>
            `;
        }).join('');
    }

    // Expose cancelJob to global scope for onclick
    window.cancelJob = async (jobId) => {
        if (!confirm('Are you sure you want to cancel this tweet?')) return;

        try {
            const response = await fetch(`/api/jobs/${jobId}/cancel`, {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                showToast('Job cancelled', false);
                loadHistory();
            } else {
                showToast(result.error || 'Failed to cancel', true);
            }
        } catch (error) {
            showToast('Network error', true);
        }
    };

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // --- Scheduling Modal ---
    // ... (existing code) ...

    // --- Submission ---
    postBtn.addEventListener('click', async () => {
        // ... (existing code) ...

        try {
            const response = await fetch('/tweet/post', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                showToast(result.message || 'Success!', false);
                // Reset form
                tweetText.value = '';
                mediaInput.value = '';
                mediaPreview.style.display = 'none';
                scheduleTime.value = '';
                confirmedScheduleTime = null; // Reset confirmed time
                nyTimeDisplay.textContent = 'Select time...';
                updatePostButtonText();
                updateState();

                // Reload history
                loadHistory();
            } else {
                showToast(result.message || 'Failed to post', true);
            }
        } catch (error) {
            // ...
        } finally {
            // ...
        }
    });
    // Check saved preference
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);

    themeToggle.addEventListener('click', () => {
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        setTheme(newTheme);
    });

    function setTheme(theme) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        const icon = themeToggle.querySelector('i');
        if (theme === 'dark') {
            icon.className = 'fas fa-moon';
        } else {
            icon.className = 'fas fa-sun';
        }
    }

    // --- Text Input & Validation ---
    tweetText.addEventListener('input', updateState);

    function updateState() {
        const text = tweetText.value.trim();
        const hasMedia = mediaInput.files.length > 0;
        const length = text.length;

        // Update char count (simple approximation)
        // Twitter uses weighted counting, but simple length is fine for MVP
        // Update to 25000 for Twitter Blue support
        const limit = 25000;
        const remaining = limit - length;

        // Only show if close to limit or negative
        if (remaining <= 100 || remaining < 0) {
            charCount.textContent = remaining;
        } else {
            charCount.textContent = '';
        }

        if (remaining < 0) {
            charCount.classList.add('danger');
            charCount.classList.remove('warning');
        } else if (remaining <= 20) {
            charCount.classList.add('warning');
            charCount.classList.remove('danger');
        } else {
            charCount.classList.remove('warning', 'danger');
        }

        // Enable/Disable Post Button
        if ((text.length > 0 || hasMedia) && remaining >= 0) {
            postBtn.disabled = false;
        } else {
            postBtn.disabled = true;
        }
    }

    // --- Media Upload ---
    mediaInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewImg.src = e.target.result;
                mediaPreview.style.display = 'block';
                updateState();
            };
            reader.readAsDataURL(file);
        }
    });

    removeMedia.addEventListener('click', () => {
        mediaInput.value = '';
        mediaPreview.style.display = 'none';
        previewImg.src = '';
        updateState();
    });

    // --- Scheduling Modal ---
    scheduleBtn.addEventListener('click', () => {
        scheduleModal.classList.add('active');
        // Set min time to now if empty
        if (!scheduleTime.value) {
            const now = new Date();
            now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
            scheduleTime.min = now.toISOString().slice(0, 16);
        }
    });

    function closeModal() {
        scheduleModal.classList.remove('active');
    }

    closeScheduleModal.addEventListener('click', closeModal);

    // Close on click outside
    scheduleModal.addEventListener('click', (e) => {
        if (e.target === scheduleModal) {
            closeModal();
        }
    });

    // Time Conversion Logic
    scheduleTime.addEventListener('input', updateNYTime);

    function updateNYTime() {
        if (!scheduleTime.value) {
            nyTimeDisplay.textContent = 'Select time...';
            return;
        }

        const date = new Date(scheduleTime.value);

        // Format to New York time
        const options = {
            timeZone: 'America/New_York',
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true,
            timeZoneName: 'short'
        };

        try {
            const formatter = new Intl.DateTimeFormat('en-US', options);
            nyTimeDisplay.textContent = formatter.format(date);
        } catch (e) {
            nyTimeDisplay.textContent = 'Invalid Date';
        }
    }

    // Confirm & Clear
    confirmScheduleBtn.addEventListener('click', () => {
        if (scheduleTime.value) {
            confirmedScheduleTime = scheduleTime.value;
            updatePostButtonText();
            closeModal();
            showToast('Schedule confirmed', false);
        } else {
            showToast('Please select a time', true);
        }
    });

    clearScheduleBtn.addEventListener('click', () => {
        scheduleTime.value = '';
        confirmedScheduleTime = null;
        nyTimeDisplay.textContent = 'Select time...';
        updatePostButtonText();
        closeModal();
    });

    function updatePostButtonText() {
        if (confirmedScheduleTime) {
            postBtn.textContent = 'Schedule';
            scheduleBtn.style.color = 'var(--primary-color)'; // Highlight icon
        } else {
            postBtn.textContent = 'Post';
            scheduleBtn.style.color = ''; // Reset icon color
        }
    }

    // --- Submission ---
    postBtn.addEventListener('click', async () => {
        const content = tweetText.value;
        const file = mediaInput.files[0];
        const scheduledTime = confirmedScheduleTime;

        const formData = new FormData();
        formData.append('content', content);
        if (file) {
            formData.append('images', file);
        }
        if (confirmedScheduleTime) {
            // Get the date object from the input (which is local time)
            const dateObj = new Date(confirmedScheduleTime);
            // Convert to ISO string with timezone (e.g., 2023-01-01T12:00:00.000Z)
            // or send as is but let backend know it's local time?
            // Best approach: Send ISO string which is always UTC
            formData.append('scheduled_time', dateObj.toISOString());
            formData.append('timezone', 'UTC'); // Tell backend this is UTC
        }

        // Disable button and show loading state
        postBtn.disabled = true;
        const originalText = postBtn.textContent;
        postBtn.textContent = 'Sending...';

        try {
            const response = await fetch('/tweet/post', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                showToast(result.message || 'Success!', false);
                // Reset form
                tweetText.value = '';
                mediaInput.value = '';
                mediaPreview.style.display = 'none';
                scheduleTime.value = '';
                confirmedScheduleTime = null; // Reset confirmed time
                nyTimeDisplay.textContent = 'Select time...';
                updatePostButtonText();
                updateState();

                // Reload history
                loadHistory();
            } else {
                showToast(result.message || 'Failed to post', true);
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Network error occurred', true);
        } finally {
            postBtn.disabled = false;
            postBtn.textContent = originalText;
            updateState(); // Re-check state
        }
    });

    // --- Toast Notification ---
    function showToast(message, isError) {
        toast.textContent = message;
        toast.className = isError ? 'toast show error' : 'toast show';
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
});
