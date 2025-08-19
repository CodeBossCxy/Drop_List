// const socket = new WebSocket("wss://10.1.3.54:8002/ws");
const messages = document.getElementById("messages");

// Function to get barcode image URL for a location
function getBarcodeUrl(location) {
    return `https://barcode.orcascan.com/?type=qr&data=${location}`;
}

// Function to create a row element
function createRowElement(data) {
    const row = document.createElement("tr");
    row.classList.add("adding-row");
    
    row.innerHTML = `
        <td>${data.serial_no}</td>
        <td>${data.part_no}</td>
        <td>${data.revision}</td>
        <td>${data.quantity}</td>
        <td>${data.location}</td>
        <td><img src="${getBarcodeUrl(data.location)}" alt="Barcode for ${data.location}" class="barcode-img"></td>
        <td>${data.deliver_to}</td>
        <td>
            <button class="delete-btn" onclick="handleDelete('${data.serial_no}', this)">
                Delete
            </button>
        </td>
    `;
    
    return row;
}

// Define the correct passcode (you can change this to your desired passcode)
const CORRECT_PASSCODE = "1234";

// Function to show passcode popup
function showPasscodePopup() {
    return new Promise((resolve) => {
        // Create a custom modal using Bootstrap's modal component
        const modalHTML = `
            <div class="modal fade" id="passcodeModal" tabindex="-1" aria-labelledby="passcodeModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="passcodeModalLabel">Enter Passcode</h5>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label for="passcodeInput" class="form-label">Please enter the passcode to delete this request:</label>
                                <input type="password" class="form-control" id="passcodeInput" placeholder="Enter numbers only" maxlength="10">
                                <div id="passcodeError" class="text-danger mt-2" style="display: none;"></div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-danger" id="confirmDeleteBtn">Delete</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove any existing modal
        const existingModal = document.getElementById('passcodeModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        const modal = new bootstrap.Modal(document.getElementById('passcodeModal'));
        const passcodeInput = document.getElementById('passcodeInput');
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        const errorDiv = document.getElementById('passcodeError');
        
        // Restrict input to numbers only
        passcodeInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });
        
        // Handle Enter key in input field
        passcodeInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                confirmBtn.click();
            }
        });
        
        // Handle confirm button click
        confirmBtn.addEventListener('click', function() {
            const enteredPasscode = passcodeInput.value.trim();
            
            if (!enteredPasscode) {
                errorDiv.textContent = 'Please enter a passcode';
                errorDiv.style.display = 'block';
                return;
            }
            
            if (enteredPasscode === CORRECT_PASSCODE) {
                modal.hide();
                resolve(true); // Passcode correct
            } else {
                errorDiv.textContent = 'Incorrect passcode. Please try again.';
                errorDiv.style.display = 'block';
                passcodeInput.value = '';
                passcodeInput.focus();
            }
        });
        
        // Handle modal close
        document.getElementById('passcodeModal').addEventListener('hidden.bs.modal', function() {
            if (!document.querySelector('.modal.show')) {
                // Only resolve false if modal was closed without successful validation
                resolve(false);
            }
            this.remove();
        });
        
        // Enhanced auto-focus functionality
        modal.show();
        
        // Multiple focus attempts to ensure it works reliably
        const focusInput = () => {
            passcodeInput.focus();
            passcodeInput.select(); // Also select any existing text
        };
        
        // Immediate focus attempt
        setTimeout(focusInput, 100);
        
        // Backup focus when modal is fully shown
        document.getElementById('passcodeModal').addEventListener('shown.bs.modal', function() {
            focusInput();
        });
        
        // Additional backup focus
        setTimeout(focusInput, 500);
    });
}

// Function to handle delete button click
async function handleDelete(serialNo, button) {
    console.log(`🗑️ Delete button clicked for serial: ${serialNo}`);
    
    // Show passcode popup and wait for validation
    const isPasscodeValid = await showPasscodePopup();
    
    if (!isPasscodeValid) {
        console.log('❌ Delete cancelled - invalid passcode or user cancelled');
        return; // Exit without deleting
    }
    
    console.log('✅ Passcode validated - hiding row immediately');
    
    // Get row reference and hide it immediately after passcode validation
    const row = button.closest('tr');
    const originalOpacity = row.style.opacity;
    const originalRowHTML = row.innerHTML; // Store original content for potential restore
    
    // Hide row immediately with visual feedback
    row.style.opacity = '0';
    row.style.transition = 'opacity 0.3s ease';
    
    try {
        console.log('🌐 Making API call to delete request');
        const response = await fetch(`/api/requests/${serialNo}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            console.log('✅ Delete request successful - removing row from DOM');
            
            // Remove row from DOM after successful API call
            setTimeout(() => {
                row.remove();
            }, 300); // Short delay to complete the fade animation
            
            // Show success message
            showAlert('Success', `Request for container ${serialNo} has been deleted.`, 'success');
        } else {
            console.error('❌ Failed to delete request - server error, restoring row');
            
            // Restore row visibility if API call failed
            row.style.opacity = originalOpacity || '1';
            showAlert('Error', 'Failed to delete request. Please try again.', 'danger');
        }
    } catch (error) {
        console.error('❌ Error deleting request:', error);
        console.log('🔄 Restoring row due to API error');
        
        // Restore row visibility if API call failed
        row.style.opacity = originalOpacity || '1';
        showAlert('Error', 'Error deleting request. Please try again.', 'danger');
    }
}

// Function to show alert messages
function showAlert(title, message, type) {
    const alertHTML = `
        <div class="alert alert-${type} alert-dismissible fade show position-fixed" 
             style="top: 100px; right: 20px; z-index: 9999; min-width: 300px;" role="alert">
            <strong>${title}:</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', alertHTML);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
}

// Function to fetch and display requests
async function fetchAndDisplayRequests() {
    try {
        const response = await fetch('/api/requests');
        const requests = await response.json();
        
        const tbody = document.getElementById("containerTableBody");
        tbody.innerHTML = ''; // Clear existing rows
        
        requests.forEach(data => {
            const row = createRowElement(data);
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error fetching requests:', error);
    }
}

// Fetch requests when page loads
document.addEventListener('DOMContentLoaded', fetchAndDisplayRequests);

// Set up polling to refresh data every 5 seconds
setInterval(fetchAndDisplayRequests, 5000);

// socket.onopen = function(e) {
//     console.log("WebSocket connection established");
// };

// socket.onclose = function(event) {
//     console.log('WebSocket connection closed. Attempting to reconnect...');
//     setTimeout(() => {
//         socket = new WebSocket(`ws://${window.location.host}/ws`);
//     }, 1000);
// };

// socket.onerror = function(error) {
//     console.error('WebSocket error:', error);
// };

// socket.onmessage = function(event) {
//     const data = JSON.parse(event.data);
//     console.log("Received data in driver:", data);
    
//     // Handle delete signal
//     if (data.type === "delete") {
//         console.log("Processing delete signal for serial:", data.serial_no);
//         const tbody = document.getElementById("containerTableBody");
//         const rows = tbody.getElementsByTagName("tr");
//         let found = false;
        
//         for (let row of rows) {
//             const cells = row.getElementsByTagName("td");
//             if (cells[0].textContent === data.serial_no) {
//                 row.style.opacity = '0';
//                 setTimeout(() => {
//                     row.remove();
//                 }, 500);
//                 found = true;
//                 break;
//             }
//         }
        
//         if (!found) {
//             console.log("No matching row found for serial:", data.serial_no);
//         }
//         return;
//     }

//     // Handle normal container data
//     console.log("Processing normal container data");
//     const tbody = document.getElementById("containerTableBody");
//     const row = createRowElement(data);
//     tbody.appendChild(row);
    
//     console.log("Added new row to table");
// };

