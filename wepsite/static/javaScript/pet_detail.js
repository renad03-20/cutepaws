document.addEventListener('DOMContentLoaded', function() {
  const adoptionForm = document.getElementById('adoptionForm');
  
  if (adoptionForm) {
      adoptionForm.addEventListener('submit', function(e) {
          e.preventDefault();
          
          const submitBtn = this.querySelector('button[type="submit"]');
          submitBtn.disabled = true;
          submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Sending...';
          
          fetch(this.action, {
              method: 'POST',
              body: new FormData(this),
              headers: {
                  'X-Requested-With': 'XMLHttpRequest'
              }
          })
          .then(response => {
              if (!response.ok) {
                  throw new Error('Network response was not ok');
              }
              return response.json();
          })
          .then(data => {
              if (data.success) {
                  // Close modal
                  const modal = bootstrap.Modal.getInstance(document.getElementById('adoptionModal'));
                  if (modal) modal.hide();
                  
                  // Redirect to messages
                  if (data.redirect_url) {
                      window.location.href = data.redirect_url;
                  }
              } else {
                  alert(data.message || 'Error submitting application');
              }
          })
          .catch(error => {
              console.error('Error:', error);
              alert('An error occurred while submitting the application');
          })
          .finally(() => {
              submitBtn.disabled = false;
              submitBtn.innerHTML = 'Submit Application';
          });
      });
  }
});