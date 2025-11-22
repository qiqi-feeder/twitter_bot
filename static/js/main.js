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

    let confirmedScheduleTime = null;

    // --- Theme Switcher ---
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
        const remaining = 280 - length;
        charCount.textContent = remaining <= 20 ? remaining : '';

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
                scheduleSection.classList.remove('active');
                updatePostButtonText();
                updateState();
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
