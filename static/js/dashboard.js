// ════════════════════════════════════════════════════════════════
//  DASHBOARD FUNCTIONALITY - USER & ORG DASHBOARDS
// ════════════════════════════════════════════════════════════════

// ──── TAB SWITCHING ────
function showTab(tabName, element) {
  // Hide all tabs
  document.querySelectorAll('.tab-section').forEach(tab => {
    tab.classList.remove('active');
  });
  
  // Show selected tab
  const tabId = 'tab-' + tabName;
  const tab = document.getElementById(tabId);
  if (tab) {
    tab.classList.add('active');
    
    // Update topbar title
    const titles = {
      'home': 'My Dashboard',
      'report': 'Report a Stray Animal',
      'tracking': 'Track Rescue Progress',
      'browse': 'Browse Rescued Animals',
      'saved': 'Saved Animals',
      'adoption': 'Adoption Interest',
      'adoption-inquiries': 'Adoption Inquiries',
      'notifications': 'Notifications',
    };
    const titleEl = document.getElementById('topbar-title');
    if (titleEl) titleEl.textContent = titles[tabName] || 'Dashboard';
  }
  
  // Update active nav item
  if (element) {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.remove('active');
    });
    element.classList.add('active');
  }
}

// ──── MODAL MANAGEMENT ────
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }
}

function openInterestForAnimal(animalId) {
  const select = document.getElementById('interestModalAnimalId');
  if (select) {
    select.value = animalId;
  }
  openModal('interestModal');
}

// Close modals on backdrop click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      closeModal(overlay.id);
    }
  });
});

// ──── SIDEBAR TOGGLE ────
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) {
    sidebar.classList.toggle('open');
  }
}

// Attach sidebar nav handlers by data-tab attribute
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.nav-item').forEach(btn => {
    let tabName = btn.dataset.tab;
    if (!tabName) {
      const onclick = btn.getAttribute('onclick') || '';
      const match = onclick.match(/showTab\(['\"]([^'\"]+)['\"]/);
      if (match) {
        tabName = match[1];
        btn.dataset.tab = tabName;
      }
    }

    if (tabName) {
      btn.addEventListener('click', (e) => {
        showTab(tabName, btn);
      });
    }
  });

  const params = new URLSearchParams(window.location.search);
  const requestedTab = params.get('tab');
  if (requestedTab) {
    let navButton = document.querySelector(`.nav-item[data-tab="${requestedTab}"]`);
    if (!navButton) {
      navButton = Array.from(document.querySelectorAll('.nav-item')).find(btn => {
        const onclick = btn.getAttribute('onclick') || '';
        return onclick.includes(`showTab('${requestedTab}'`) || onclick.includes(`showTab(\"${requestedTab}\"`);
      });
    }

    if (navButton) {
      showTab(requestedTab, navButton);
    } else {
      showTab(requestedTab);
    }
  }

  initLiveSearch();
});

function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

function initLiveSearch() {
  document.querySelectorAll('.live-search-form').forEach(form => {
    const input = form.querySelector('[name="q"]');
    if (!input) return;

    const loading = form.querySelector('.search-loading');
    const debouncedSubmit = debounce(() => {
      if (loading) {
        loading.style.display = 'inline-block';
      }
      form.submit();
    }, 400);

    input.addEventListener('input', () => {
      if (loading) {
        loading.style.display = 'inline-block';
      }
      debouncedSubmit();
    });

    form.addEventListener('submit', () => {
      if (loading) {
        loading.style.display = 'inline-block';
      }
    });
  });
}

// ──── HEART BUTTON / SAVE ANIMAL ────
function toggleSave(event, button) {
  event.stopPropagation();
  event.preventDefault();
  
  const card = button.closest('.animal-card');
  const animalId = (card && card.dataset.animalId) || button.dataset.animalId;
  if (!animalId) {
    console.error('Animal ID not found');
    return;
  }
  
  const isSaved = button.classList.contains('saved');
  button.classList.toggle('saved');
  const newState = button.classList.contains('saved');
  
  fetch(`/api/animal/${animalId}/toggle-save/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-CSRFToken': getCsrfToken(),
    },
  })
  .then(r => r.json())
  .then(data => {
    if (data.saved && !newState) {
      button.classList.add('saved');
    } else if (!data.saved && newState) {
      button.classList.remove('saved');
    }
    if (button.id === 'animalModalSaveBtn') {
      button.textContent = data.saved ? '❤️ Saved' : '🤍 Save Animal';
    }
  })
  .catch(err => {
    console.error('Save toggle error:', err);
    button.classList.toggle('saved', isSaved);
  });
}

// ──── BROWSE ANIMAL FILTERING ────
function getBrowseFilterState() {
  const browseTab = document.getElementById('tab-browse');
  if (!browseTab) return null;

  const searchInput = browseTab.querySelector('.filter-bar input[type="search"]');
  const selects = browseTab.querySelectorAll('.filter-bar select');

  return {
    search: searchInput?.value.trim().toLowerCase() || '',
    species: selects[0]?.value || 'All Species',
    status: selects[1]?.value || 'All Statuses',
    org: selects[2]?.value || 'All Organizations',
    chip: browseTab.querySelector('.filter-chips .chip.active')?.textContent.trim() || 'All',
  };
}

function matchesBrowseFilters(card, filters) {
  if (!filters) return true;
  const text = card.innerText.toLowerCase();

  if (filters.search && !text.includes(filters.search)) {
    return false;
  }

  if (filters.species && filters.species !== 'All Species') {
    if (filters.species === 'Dog' && !text.includes('dog')) return false;
    if (filters.species === 'Cat' && !text.includes('cat')) return false;
    if (filters.species === 'Other' && (text.includes('dog') || text.includes('cat'))) return false;
  }

  if (filters.status && filters.status !== 'All Statuses') {
    const statusText = filters.status.toLowerCase();
    if (statusText === 'under observation' && !text.includes('observation')) return false;
    if (statusText === 'recovering' && !text.includes('recovering') && !text.includes('in recovery')) return false;
    if (statusText === 'ready for adoption' && !text.includes('ready for adoption') && !text.includes('adoption ready') && !text.includes('available for adoption')) return false;
  }

  if (filters.chip && filters.chip !== 'All') {
    const chip = filters.chip.toLowerCase();
    if (chip.includes('ready for adoption') && !text.includes('adoption ready') && !text.includes('available for adoption')) return false;
    if (chip.includes('recovering') && !text.includes('recovering') && !text.includes('in recovery')) return false;
    if (chip.includes('dogs only') && !text.includes('dog')) return false;
    if (chip.includes('cats only') && !text.includes('cat')) return false;
    if (chip.includes('my saved') && !card.querySelector('.heart-btn.saved')) return false;
  }

  return true;
}

function applyBrowseFilters() {
  const filters = getBrowseFilterState();
  const cards = document.querySelectorAll('#tab-browse .animal-card');
  let visibleCount = 0;
  cards.forEach(card => {
    const show = matchesBrowseFilters(card, filters);
    card.style.display = show ? '' : 'none';
    if (show) visibleCount += 1;
  });
  const noResults = document.getElementById('browseNoResults');
  if (noResults) {
    noResults.style.display = visibleCount === 0 ? 'block' : 'none';
  }
}

function initBrowseFilterHandlers() {
  const browseTab = document.getElementById('tab-browse');
  if (!browseTab) return;

  const searchInput = browseTab.querySelector('.filter-bar input[type="search"]');
  const selects = browseTab.querySelectorAll('.filter-bar select');

  searchInput?.addEventListener('input', applyBrowseFilters);
  selects.forEach(select => select.addEventListener('change', applyBrowseFilters));
}

// ──── REPORT FILTERING (ORG ROLE) ────
function getOrgReportFilterState() {
  const tab = document.getElementById('tab-reports');
  if (!tab) return null;
  const searchInput = tab.querySelector('.filter-bar input[type="search"]');
  const selects = tab.querySelectorAll('.filter-bar select');
  return {
    search: searchInput?.value.trim().toLowerCase() || '',
    status: selects[0]?.value || 'All Statuses',
    animal: selects[1]?.value || 'All Animals',
    priority: selects[2]?.value || 'All Priority',
  };
}

function matchesOrgReportFilters(row, filters) {
  if (!filters) return true;
  const text = row.innerText.toLowerCase();
  if (filters.search && !text.includes(filters.search)) return false;
  if (filters.status && filters.status !== 'All Statuses' && !text.includes(filters.status.toLowerCase())) return false;
  if (filters.animal && filters.animal !== 'All Animals' && !text.includes(filters.animal.toLowerCase())) return false;
  if (filters.priority && filters.priority !== 'All Priority' && !text.includes(filters.priority.toLowerCase())) return false;
  return true;
}

function applyOrgReportFilters() {
  const filters = getOrgReportFilterState();
  const rows = document.querySelectorAll('#tab-reports table tbody tr:not(.no-results-row)');
  let visibleCount = 0;
  rows.forEach(row => {
    const show = matchesOrgReportFilters(row, filters);
    row.style.display = show ? '' : 'none';
    if (show) visibleCount += 1;
  });
  const placeholder = document.querySelector('#tab-reports tbody .no-results-row');
  if (placeholder) {
    placeholder.style.display = visibleCount === 0 ? 'table-row' : 'none';
  }
}

function initOrgReportFilters() {
  const tab = document.getElementById('tab-reports');
  if (!tab) return;
  const searchInput = tab.querySelector('.filter-bar input[type="search"]');
  const selects = tab.querySelectorAll('.filter-bar select');
  searchInput?.addEventListener('input', applyOrgReportFilters);
  selects.forEach(select => select.addEventListener('change', applyOrgReportFilters));
}

// ──── ORG ANIMAL FILTERING ────
function getOrgAnimalFilterState() {
  const tab = document.getElementById('tab-animals');
  if (!tab) return null;
  const searchInput = tab.querySelector('.filter-bar input[type="search"]');
  const selects = tab.querySelectorAll('.filter-bar select');
  return {
    search: searchInput?.value.trim().toLowerCase() || '',
    species: selects[0]?.value || 'All Species',
    status: selects[1]?.value || 'All Statuses',
    shelter: selects[2]?.value || 'All Shelters',
  };
}

function matchesOrgAnimalFilters(card, filters) {
  if (!filters) return true;
  const text = card.innerText.toLowerCase();
  if (filters.search && !text.includes(filters.search)) return false;
  if (filters.species && filters.species !== 'All Species') {
    if (filters.species === 'Dog' && !text.includes('dog')) return false;
    if (filters.species === 'Cat' && !text.includes('cat')) return false;
  }
  if (filters.status && filters.status !== 'All Statuses') {
    const status = filters.status.toLowerCase();
    if (status === 'under observation' && !text.includes('observation')) return false;
    if (status === 'recovering' && !text.includes('recovering')) return false;
    if (status === 'ready for adoption' && !text.includes('adoption ready') && !text.includes('available for adoption')) return false;
    if (status === 'adopted' && !text.includes('adopted')) return false;
  }
  if (filters.shelter && filters.shelter !== 'All Shelters' && !text.includes(filters.shelter.toLowerCase())) return false;
  return true;
}

function applyOrgAnimalFilters() {
  const filters = getOrgAnimalFilterState();
  const cards = document.querySelectorAll('#tab-animals .animal-card');
  let visibleCount = 0;
  cards.forEach(card => {
    const show = matchesOrgAnimalFilters(card, filters);
    card.style.display = show ? '' : 'none';
    if (show) visibleCount += 1;
  });
  const noResults = document.getElementById('orgAnimalsNoResults');
  if (noResults) {
    noResults.style.display = visibleCount === 0 ? 'block' : 'none';
  }
}

function initOrgAnimalFilters() {
  const tab = document.getElementById('tab-animals');
  if (!tab) return;
  const searchInput = tab.querySelector('.filter-bar input[type="search"]');
  const selects = tab.querySelectorAll('.filter-bar select');
  searchInput?.addEventListener('input', applyOrgAnimalFilters);
  selects.forEach(select => select.addEventListener('change', applyOrgAnimalFilters));
}

function renderAdoptionInquiries(inquiries) {
  const tableBody = document.getElementById('adoptionInquiryTableBody');
  const inquiryList = document.getElementById('adoptionInquiryList');

  if (!tableBody || !inquiryList) return;

  const countsByAnimal = inquiries.reduce((acc, inquiry) => {
    const key = inquiry.animal_name || 'Unknown animal';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});

  const animals = Array.from(new Set(inquiries.map(inquiry => inquiry.animal_name || 'Unknown animal')));

  if (!inquiries.length) {
    tableBody.innerHTML = '<tr class="no-results-row"><td colspan="7" style="text-align:center;padding:1.25rem;color:var(--muted)">No adoption inquiries yet.</td></tr>';
    inquiryList.innerHTML = '<div class="msg-item"><div class="msg-avatar">👤</div><div class="msg-body"><div class="msg-from">No adoption inquiries yet.</div></div></div>';
    return;
  }

  const rows = animals.map(animalName => {
    const animalInquiries = inquiries.filter(inquiry => (inquiry.animal_name || 'Unknown animal') === animalName);
    const firstInquiry = animalInquiries[0] || {};
    const statusText = firstInquiry.status || 'pending';
    const statusLabel = statusText === 'approved' ? 'Active' : statusText === 'rejected' ? 'Inactive' : 'Pending';
    const badgeClass = statusText === 'approved' ? 'badge-adoption' : statusText === 'rejected' ? 'badge-pending' : 'badge-observation';
    const animalDisplayName = animalName || 'Unknown animal';
    const animalSpecies = firstInquiry.animal_species || 'Unknown';
    const animalAge = firstInquiry.animal_age || 'Unknown';
    const animalShelter = firstInquiry.rescue_org_name || 'This organization';

    return `
      <tr>
        <td><div class="animal-cell"><div class="animal-thumb">🐾</div><div><div class="animal-name">${animalDisplayName}</div><div class="animal-sub">${animalSpecies} · ${animalAge}</div></div></div></td>
        <td>${animalSpecies}</td>
        <td>${animalAge}</td>
        <td>${animalShelter}</td>
        <td><span style="font-size:.84rem;font-weight:600;color:var(--teal)">${countsByAnimal[animalName] || 0} inquiry${(countsByAnimal[animalName] || 0) === 1 ? '' : 'ies'}</span></td>
        <td>
          <label class="toggle" data-animal-id="${firstInquiry.animal_id || ''}">
            <input type="checkbox" ${statusText === 'approved' ? 'checked' : ''} onchange="toggleAnimalAdoption(${firstInquiry.animal_id || 0})">
            <div class="toggle-track"><div class="toggle-thumb"></div></div>
            <span class="toggle-label">${statusLabel}</span>
          </label>
        </td>
        <td><div style="display:flex;gap:.4rem"><button class="btn btn-sm btn-outline">Inquiries</button><button class="btn btn-sm btn-teal">Contact</button></div></td>
      </tr>
    `;
  }).join('');

  tableBody.innerHTML = rows;

  inquiryList.innerHTML = inquiries.map(inquiry => {
    const preview = (inquiry.message || '').trim();
    const previewText = preview.length > 110 ? `${preview.slice(0, 107)}…` : preview || 'No message provided.';
    const createdAt = inquiry.created_at ? new Date(inquiry.created_at).toLocaleString() : 'Unknown date';
    return `
      <div class="msg-item">
        <div class="msg-avatar">👤</div>
        <div class="msg-body">
          <div class="msg-from">${inquiry.user_name || 'Anonymous'} <span style="font-size:.75rem;color:var(--muted);font-weight:400">— inquiring about ${inquiry.animal_name || 'an animal'}</span></div>
          <div class="msg-preview">${previewText}</div>
          <div style="font-size:.74rem;color:var(--muted);margin-top:.25rem">${(inquiry.living_situation || 'Unknown').replace(/_/g, ' ')} · ${inquiry.other_pets || 'No pets'} · ${createdAt}</div>
        </div>
        <div><div class="msg-time">${createdAt}</div></div>
      </div>
    `;
  }).join('');
}

function loadAdoptionInquiries() {
  fetch('/api/adoption-inquiries/', {
    headers: {
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
  })
  .then(async response => {
    const data = await response.json().catch(() => []);
    if (!response.ok) throw new Error('Unable to load adoption inquiries');
    renderAdoptionInquiries(Array.isArray(data) ? data : []);
  })
  .catch(() => {
    const tableBody = document.getElementById('adoptionInquiryTableBody');
    const inquiryList = document.getElementById('adoptionInquiryList');
    if (tableBody) {
      tableBody.innerHTML = '<tr class="no-results-row"><td colspan="7" style="text-align:center;padding:1.25rem;color:var(--muted)">Unable to load adoption inquiries.</td></tr>';
    }
    if (inquiryList) {
      inquiryList.innerHTML = '<div class="msg-item"><div class="msg-avatar">👤</div><div class="msg-body"><div class="msg-from">Unable to load adoption inquiries.</div></div></div>';
    }
  });
}

function getAnimalStatusDisplay(status) {
  switch (status) {
    case 'adoption':
      return 'Ready for Adoption';
    case 'adopted':
      return 'Adopted';
    case 'recovering':
      return 'Recovering';
    case 'observation':
      return 'Under Observation';
    default:
      return 'Under Observation';
  }
}

function getAnimalSpeciesDisplay(species) {
  switch (species) {
    case 'cat':
      return 'Cat';
    case 'other':
      return 'Other';
    default:
      return 'Dog';
  }
}

function getAnimalSexDisplay(sex) {
  switch (sex) {
    case 'female':
      return 'Female';
    case 'male':
      return 'Male';
    default:
      return 'Unknown';
  }
}

function getAnimalBadgeClass(status, adoptionOpen) {
  if (adoptionOpen) return 'badge-adoption';
  if (status === 'adopted') return 'badge-adopted';
  if (status === 'recovering') return 'badge-recovering';
  if (status === 'observation') return 'badge-observation';
  return 'badge-pending';
}

function updateOrgAnimalData(animalId, values) {
  if (!Array.isArray(window.orgAnimals)) return;
  const animal = window.orgAnimals.find(item => item.id === animalId);
  if (!animal) return;

  animal.name = values.name || animal.name || '';
  animal.species = values.species || animal.species || 'dog';
  animal.sex = values.sex || animal.sex || 'unknown';
  animal.approx_age = values.approx_age || animal.approx_age || '';
  animal.breed = values.breed || animal.breed || '';
  animal.color = values.color || animal.color || '';
  animal.status = values.status || animal.status || 'observation';
  animal.vaccination = values.vaccination || animal.vaccination || 'none';
  animal.shelter = values.shelter || animal.shelter || '';
  animal.medical_notes = values.medical_notes || animal.medical_notes || '';
  animal.temperament = values.temperament || animal.temperament || '';
  animal.adoption_open = Boolean(values.adoption_open);
  animal.status_display = getAnimalStatusDisplay(animal.status);
  animal.species_display = getAnimalSpeciesDisplay(animal.species);
  animal.sex_display = getAnimalSexDisplay(animal.sex);
}

function updateAnimalCardUI(animalId, values) {
  const card = document.querySelector(`.animal-card[data-animal-id="${animalId}"]`);
  if (!card) return;

  const nameEl = card.querySelector('.animal-card-name');
  if (nameEl) {
    nameEl.textContent = values.name || 'Unnamed';
  }

  const metaEl = card.querySelector('.animal-card-meta');
  if (metaEl) {
    const speciesDisplay = getAnimalSpeciesDisplay(values.species || 'dog');
    const sexDisplay = getAnimalSexDisplay(values.sex || 'unknown');
    const breed = values.breed || 'Unknown';
    const approxAge = values.approx_age || 'Unknown';
    const shelter = values.shelter || 'No shelter';
    metaEl.textContent = `${sexDisplay} · ${speciesDisplay} · ${breed} · ${approxAge} · ${shelter}`;
  }

  const badgeEl = card.querySelector('.animal-img-badge .badge');
  if (badgeEl) {
    const status = values.status || 'observation';
    const adoptionOpen = Boolean(values.adoption_open);
    badgeEl.textContent = `${getAnimalStatusDisplay(status)}${adoptionOpen ? ' · Adoption Open' : ''}`;
    badgeEl.className = `badge ${getAnimalBadgeClass(status, adoptionOpen)}`;
  }
}

function submitAnimalEditForm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form || !form.action) return;

  const animalIdInput = form.querySelector('#currentEditAnimalId');
  const animalId = animalIdInput?.value;
  const formData = new FormData(form);
  const adoptionOpen = form.querySelector('#animalEditAdoptionOpen')?.checked || false;
  formData.set('adoption_open', adoptionOpen ? 'on' : '');

  fetch(form.action, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'X-Requested-With': 'XMLHttpRequest',
      'Accept': 'application/json',
    },
    body: formData,
  })
  .then(async response => {
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Animal update failed');
    return data;
  })
  .then(data => {
    if (!data.ok) throw new Error('Animal update failed');

    closeModal('animalEditModal');
    openModal('animalEditSuccessModal');

    if (animalId) {
      const values = {
        name: formData.get('name') || '',
        species: formData.get('species') || 'dog',
        sex: formData.get('sex') || 'unknown',
        approx_age: formData.get('approx_age') || '',
        breed: formData.get('breed') || '',
        color: formData.get('color') || '',
        status: formData.get('status') || 'observation',
        vaccination: formData.get('vaccination') || 'none',
        shelter: formData.get('shelter') || '',
        medical_notes: formData.get('medical_notes') || '',
        temperament: formData.get('temperament') || '',
        adoption_open: adoptionOpen,
      };
      updateOrgAnimalData(Number(animalId), values);
      updateAnimalCardUI(Number(animalId), values);
    }
  })
  .catch(() => {
    alert('Failed to update animal profile. Please try again.');
  });
}

document.addEventListener('DOMContentLoaded', () => {
  const animalEditForm = document.getElementById('animalEditForm');
  if (animalEditForm) {
    animalEditForm.addEventListener('submit', submitAnimalEditForm);
  }
  loadAdoptionInquiries();
});

// ──── ANIMAL CARD DETAIL MODAL ────
async function openAnimalCard(event, animalId) {
  if (event) event.stopPropagation();
  if (!animalId) return;

  try {
    const response = await fetch(`/api/animal/${animalId}/detail/`);
    if (!response.ok) throw new Error('Unable to load animal details');
    const data = await response.json();
    populateAnimalModal(data);
    openModal('animalProfileModal');
  } catch (err) {
    console.error('Error opening animal card:', err);
    alert('Unable to load animal details. Please try again later.');
  }
}

function populateAnimalModal(data) {
  const avatar = document.getElementById('animalModalAvatar');
  const name = document.getElementById('animalModalName');
  const subtitle = document.getElementById('animalModalSubtitle');
  const statusBadge = document.getElementById('animalModalStatusBadge');
  const vaxBadge = document.getElementById('animalModalVaxBadge');
  const orgText = document.getElementById('animalModalOrg');
  const rescuedAt = document.getElementById('animalModalRescuedAt');
  const medicalStatus = document.getElementById('animalModalMedicalStatus');
  const vaccination = document.getElementById('animalModalVaccination');
  const temperament = document.getElementById('animalModalTemperament');
  const description = document.getElementById('animalModalDescription');
  const saveBtn = document.getElementById('animalModalSaveBtn');
  const interestBtn = document.getElementById('animalModalInterestBtn');

  if (avatar) {
    avatar.innerHTML = data.photo_url ? `<img src="${data.photo_url}" alt="${data.name}" style="width:100%;height:100%;object-fit:cover;border-radius:16px;">` : (data.species === 'dog' ? '🐕' : data.species === 'cat' ? '🐈' : '🐾');
  }
  if (name) name.textContent = data.name || 'Unnamed Animal';
  if (subtitle) subtitle.textContent = `${data.species || 'Unknown species'} · ${data.approx_age || 'Unknown age'} · ${data.sex || 'Unknown'}`;
  if (statusBadge) {
    statusBadge.textContent = data.status || 'Status';
    statusBadge.className = `badge ${data.status === 'Ready for Adoption' ? 'badge-adoption' : data.status === 'Recovering' ? 'badge-recovery' : data.status === 'Under Observation' ? 'badge-submitted' : 'badge'}`;
  }
  if (vaxBadge) vaxBadge.textContent = data.vaccination || 'Vaccination';
  if (orgText) orgText.textContent = `${data.rescue_org || 'Unknown'} · ${data.shelter || 'Unknown shelter'}`;
  if (rescuedAt) rescuedAt.textContent = data.rescued_at || 'Unknown';
  if (medicalStatus) medicalStatus.textContent = data.medical_notes || 'Not available';
  if (vaccination) vaccination.textContent = data.vaccination || 'Not available';
  if (temperament) temperament.textContent = data.temperament || 'Not available';
  if (description) description.textContent = `This animal is currently listed as ${data.status || 'available'} with ${data.rescue_org || 'a rescue organization'}. ${data.medical_notes ? 'Medical notes: ' + data.medical_notes : 'No additional medical notes provided.'}`;

  if (saveBtn) {
    saveBtn.dataset.animalId = data.id;
    saveBtn.classList.toggle('saved', data.is_saved);
    saveBtn.textContent = data.is_saved ? '❤️ Saved' : '🤍 Save Animal';
  }
  if (interestBtn) interestBtn.dataset.animalId = data.id;
}

let reportMap = null;
let reportPin = null;

function initReportMap() {
  const mapContainer = document.getElementById('reportMap');
  if (!mapContainer || typeof L === 'undefined') return;

  const defaultCenter = [14.5896, 120.9786];
  reportMap = L.map(mapContainer, {
    center: defaultCenter,
    zoom: 12,
    scrollWheelZoom: false,
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(reportMap);

  reportMap.on('click', function (e) {
    placeReportPin(e.latlng);
  });
}

function placeReportPin(latlng) {
  if (!reportMap) return;
  if (reportPin) {
    reportPin.setLatLng(latlng);
  } else {
    reportPin = L.marker(latlng, { draggable: true }).addTo(reportMap);
    reportPin.on('dragend', function (dragEvent) {
      const position = dragEvent.target.getLatLng();
      updateReportLocationFields(position.lat, position.lng, true);
    });
  }
  updateReportLocationFields(latlng.lat, latlng.lng, true);
}

function clearReportPin() {
  if (reportPin && reportMap) {
    reportMap.removeLayer(reportPin);
    reportPin = null;
  }
}

function updateReportLocationFields(lat, lng, reverseGeocode = false) {
  const latInput = document.getElementById('reportLatitude');
  const lngInput = document.getElementById('reportLongitude');
  if (latInput) latInput.value = lat.toFixed(6);
  if (lngInput) lngInput.value = lng.toFixed(6);
  if (reverseGeocode) {
    fetchAddressFromLatLng(lat, lng);
  }
}

function fetchAddressFromLatLng(lat, lng) {
  const addressInput = document.querySelector('#tab-report input[name="address"]');
  if (!addressInput) return;

  fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lng)}`)
    .then(r => r.json())
    .then(data => {
      if (data && data.display_name) {
        addressInput.value = data.display_name;
      }
    })
    .catch(() => {
      // Silent failure; keep explicit address entry available.
    });
}

function initPhotoPreview() {
  const photoInput = document.getElementById('reportPhotosInput');
  const previewContainer = document.getElementById('reportPreviewContainer');
  const uploadZone = document.getElementById('reportUploadZone');

  if (!photoInput || !previewContainer || !uploadZone) return;

  const setInputFiles = (files) => {
    const dt = new DataTransfer();
    files.forEach(file => dt.items.add(file));
    photoInput.files = dt.files;
    renderPreviews(Array.from(dt.files));
  };

  const renderPreviews = (files) => {
    previewContainer.innerHTML = '';
    if (!files.length) {
      previewContainer.style.display = 'none';
      return;
    }
    previewContainer.style.display = 'flex';
    files.slice(0, 5).forEach((file, index) => {
      const item = document.createElement('div');
      item.className = 'preview-item';
      item.innerHTML = `
        <img src="${URL.createObjectURL(file)}" alt="Preview" loading="lazy">
        <button type="button" class="preview-remove" data-index="${index}" title="Remove photo">✕</button>
      `;
      const removeButton = item.querySelector('.preview-remove');
      removeButton.addEventListener('click', () => {
        const currentFiles = Array.from(photoInput.files || []);
        currentFiles.splice(index, 1);
        setInputFiles(currentFiles);
      });
      previewContainer.appendChild(item);
    });
  };

  const normalizeFiles = (files) => {
    const validFiles = Array.from(files || []).filter(file => file.type.startsWith('image/'));
    return validFiles.slice(0, 5);
  };

  const clearPreview = () => {
    previewContainer.innerHTML = '';
    previewContainer.style.display = 'none';
  };

  photoInput.addEventListener('change', () => {
    const files = normalizeFiles(photoInput.files);
    setInputFiles(files);
  });

  uploadZone.addEventListener('click', () => photoInput.click());
  uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const files = normalizeFiles(e.dataTransfer.files);
    if (!files.length) return;
    const existingFiles = Array.from(photoInput.files || []);
    setInputFiles(existingFiles.concat(files).slice(0, 5));
  });
}

function validateReportFiles(fileList) {
  const files = Array.from(fileList || []);
  if (files.length > 5) {
    return 'You may upload up to 5 photos.';
  }
  for (const file of files) {
    if (!file.type.startsWith('image/')) {
      return 'Only image files are allowed for report photos.';
    }
    if (file.size > 5 * 1024 * 1024) {
      return 'Each photo must be smaller than 5MB.';
    }
  }
  return '';
}

function resetReportForm(reportSection) {
  if (!reportSection) return;
  reportSection.querySelector('select[name="animal_type"]').value = '';
  reportSection.querySelector('select[name="condition"]').value = '';
  reportSection.querySelector('textarea[name="description"]').value = '';
  reportSection.querySelector('input[name="address"]').value = '';
  const latInput = reportSection.querySelector('input[name="latitude"]');
  if (latInput) latInput.value = '';
  const lngInput = reportSection.querySelector('input[name="longitude"]');
  if (lngInput) lngInput.value = '';
  const emergencyInputs = reportSection.querySelectorAll('input[name="emergency"]');
  emergencyInputs.forEach(input => {
    input.checked = input.value === 'critical';
  });
  const photoInput = reportSection.querySelector('input[name="photos"]');
  if (photoInput) {
    photoInput.value = '';
    const event = new Event('change', { bubbles: true });
    photoInput.dispatchEvent(event);
  }
  clearReportPin();
}

function submitReport(event) {
  event?.preventDefault();
  const submitButton = event?.currentTarget;
  const reportSection = document.getElementById('tab-report') || document;
  
  const animal_type = reportSection.querySelector('select[name="animal_type"]')?.value;
  const condition = reportSection.querySelector('select[name="condition"]')?.value;
  const priority = reportSection.querySelector('input[name="emergency"]:checked')?.value || 'normal';
  const description = reportSection.querySelector('textarea[name="description"]')?.value.trim();
  const location = reportSection.querySelector('input[name="address"]')?.value.trim();
  const latitude = reportSection.querySelector('input[name="latitude"]')?.value.trim();
  const longitude = reportSection.querySelector('input[name="longitude"]')?.value.trim();
  const photoInput = reportSection.querySelector('input[name="photos"]');
  
  if (!animal_type || !condition || !description || !location) {
    alert('Please fill in all required fields.');
    return;
  }
  const fileValidation = validateReportFiles(photoInput?.files);
  if (fileValidation) {
    alert(fileValidation);
    return;
  }
  if (submitButton) submitButton.disabled = true;
  
  const formData = new FormData();
  formData.append('animal_type', animal_type);
  formData.append('condition', condition);
  formData.append('priority', priority);
  formData.append('description', description);
  formData.append('location', location);
  if (latitude) formData.append('latitude', latitude);
  if (longitude) formData.append('longitude', longitude);
  if (photoInput) {
    Array.from(photoInput.files || []).forEach((file, index) => {
      if (index === 0) {
        formData.append('photo', file);
      } else {
        formData.append('photos', file);
      }
    });
  }
  
  fetch('/api/report/submit/', {
  method: 'POST',
  headers: {
    'X-CSRFToken': getCsrfToken(),
    'X-Requested-With': 'XMLHttpRequest',
  },
  body: formData,
})
  .then(async r => {
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Report submission failed');
    return data;
  })
  .then(data => {
    if (data.ok) {
      document.querySelectorAll('[data-report-number]').forEach(el => {
        el.textContent = '#' + data.report_number;
      });
      openModal('reportSuccessModal');
      resetReportForm(reportSection);
    }
  })
  .catch(err => {
    console.error('Report submission error:', err);
    alert(err.message || 'Unable to submit report. Please try again.');
  })
  .finally(() => {
    if (submitButton) submitButton.disabled = false;
  });
}

// ──── FILTER CHIPS ────
function filterChip(element) {
  document.querySelectorAll('.chip').forEach(chip => {
    chip.classList.remove('active');
  });
  element.classList.add('active');
  applyBrowseFilters();
}

// ──── ADOPTION INQUIRY ────
function submitInquiry(event) {
  event?.preventDefault();
  const submitButton = event?.currentTarget;
  const inquirySection = document.getElementById('tab-adoption') || document;
  
  const animal_id = inquirySection.querySelector('select[name="animal"]')?.value;
  const living_situation = inquirySection.querySelector('select[name="living_situation"]')?.value || 'house';
  const other_pets = inquirySection.querySelector('select[name="other_pets"]')?.value || 'none';
  const message = inquirySection.querySelector('textarea[name="message"]')?.value;
  
  if (!animal_id || !message) {
    alert('Please select an animal and write a message');
    return;
  }
  if (submitButton) submitButton.disabled = true;
  
  const formData = new FormData();
  formData.append('animal_id', animal_id);
  formData.append('living_situation', living_situation);
  formData.append('other_pets', other_pets);
  formData.append('message', message);
  
  fetch('/api/inquiry/submit/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
    },
    body: formData,
  })
  .then(async r => {
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Inquiry submission failed');
    return data;
  })
  .then(data => {
    if (data.ok) {
      openModal('inquirySentModal');
      inquirySection.querySelector('select[name="animal"]').value = '';
      inquirySection.querySelector('textarea[name="message"]').value = '';
    }
  })
  .catch(err => {
    console.error('Inquiry submission error:', err);
    alert(err.message || 'Unable to send inquiry. Please try again.');
  })
  .finally(() => {
    if (submitButton) submitButton.disabled = false;
  });
}

// ──── UTILITY: GET CSRF TOKEN ────
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

function getCsrfToken() {
  return getCookie('csrftoken') || document.querySelector('meta[name="csrf-token"]')?.content || '';
}

// ──── NOTIFICATION BADGE UPDATE ────
function updateNotificationBadges() {
  fetch('/api/user-notifications/')
    .then(r => r.json())
    .then(data => {
      // Update badge counts throughout page
      const unreadCount = data.unread;
      document.querySelectorAll('[data-notif-count]').forEach(el => {
        el.textContent = unreadCount;
      });
      
    })
    .catch(err => console.error('Error updating notifications:', err));
}

// Poll for notification updates every 30 seconds
setInterval(updateNotificationBadges, 30000);

// Initial update on page load
document.addEventListener('DOMContentLoaded', () => {
  updateNotificationBadges();
});

// ──── MESSAGING: send messages, include conversation_id when available ────
document.addEventListener('submit', function (e) {
  const form = e.target.closest('form.inquiry-reply-form');
  if (!form) return;

  e.preventDefault();

  const input = form.querySelector('.inquiry-reply-input');
  if (!input) return alert('Message input not found');
  const body = input.value.trim();
  if (!body) return alert('Please type a message');

  const recipient_id = form.dataset.recipientId || '';
  const conversation_id = form.dataset.conversationId || '';
  const inquiry_id = form.dataset.inquiryId || '';
  const endpoint = form.dataset.endpoint || '/api/message/send/';

  const formData = new FormData();
  formData.append('body', body);
  if (recipient_id) formData.append('recipient_id', recipient_id);
  if (conversation_id) formData.append('conversation_id', conversation_id);
  if (inquiry_id) formData.append('inquiry_id', inquiry_id);

  fetch(endpoint, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
    },
    body: formData,
  })
  .then(async r => {
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || 'Message send failed');
    return data;
  })
  .then(() => {
    input.value = '';

    const threadContainer = form.closest('.inquiry-thread-card')?.querySelector('.inquiry-thread-messages')
      || form.closest('.msg-item')?.querySelector('.inquiry-thread-messages')
      || form.closest('.card')?.querySelector('.inquiry-thread-messages');

    if (threadContainer) {
      const placeholder = threadContainer.querySelector('.padded');
      if (placeholder) placeholder.remove();

      const bubble = document.createElement('div');
      bubble.style.maxWidth = '85%';
      bubble.style.padding = '.7rem .9rem';
      bubble.style.borderRadius = '12px 12px 4px 12px';
      bubble.style.alignSelf = 'flex-end';
      bubble.style.background = 'var(--amber)';
      bubble.style.color = 'white';
      bubble.style.fontSize = '.82rem';
      bubble.innerHTML = `${escapeHtml(body)}<div style="font-size:.7rem;margin-top:.3rem;color:rgba(255,255,255,.72)">Just now · You</div>`;
      threadContainer.appendChild(bubble);
      threadContainer.scrollTop = threadContainer.scrollHeight;
    }
  })
  .catch(err => {
    console.error('Message send error:', err);
    alert(err.message || 'Unable to send message');
  });
});

document.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('click', function (e) {
    let target = e.target;
    if (target && target.nodeType !== Node.ELEMENT_NODE) {
      target = target.parentElement;
    }

    const toggle = target?.closest('.inquiry-summary-toggle');
    if (!toggle) return;

    const card = toggle.closest('.inquiry-card');
    if (!card) return;
    const panel = card.querySelector('.inquiry-detail-panel');
    if (!panel) return;

    const isOpen = !panel.hidden && panel.style.display !== 'none';
    document.querySelectorAll('.inquiry-detail-panel').forEach(p => {
      p.hidden = true;
      p.style.display = 'none';
    });

    if (!isOpen) {
      panel.hidden = false;
      panel.style.display = 'block';
      card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

document.addEventListener('submit', function (e) {
  const form = e.target.closest('form.inquiry-status-form');
  if (!form) return;

  e.preventDefault();
  const action = form.action;
  const formData = new FormData(form);

  fetch(action, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: formData,
  })
  .then(async r => {
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || 'Unable to update status');
    return data;
  })
  .then(data => {
    const card = form.closest('.inquiry-card');
    if (!card) return;
    const badges = card.querySelectorAll('.inquiry-status-badge');
    const statusLabel = data.status_display || form.querySelector('[name="status"]').selectedOptions[0].textContent;
    const statusValue = form.querySelector('[name="status"]').value;
    const badgeStyle = statusValue === 'replied'
      ? 'background:var(--teal-lt);color:#2d7a7a' : 'background:var(--gold-lt);color:#a07a10';

    badges.forEach(badge => {
      badge.textContent = statusLabel;
      badge.setAttribute('style', badgeStyle);
    });
  })
  .catch(err => {
    console.error('Status update error:', err);
    alert(err.message || 'Unable to update inquiry status');
  });
});


// ──── CLIENT: Conversations list + thread rendering ────
async function fetchConversations(activeConversationId = '') {
  try {
    const r = await fetch('/api/conversations/');
    if (!r.ok) throw new Error('Failed to load conversations');
    const data = await r.json();
    const conversations = data.conversations || [];
    renderConversations(conversations, activeConversationId);
    updateMessageNavBadge(conversations);
  } catch (err) {
    console.error('Conversations load error:', err);
    const el = document.getElementById('conversationsList');
    if (el) el.innerHTML = '<div class="padded">Unable to load conversations.</div>';
  }
}

function renderConversations(list, activeConversationId = '') {
  const container = document.getElementById('conversationsList');
  if (!container) return;
  if (!list.length) {
    container.innerHTML = '<div class="padded">No conversations yet.</div>';
    return;
  }
  container.innerHTML = '';
  list.forEach(c => {
    const item = document.createElement('div');
    item.className = 'msg-item';
    if (c.unread) item.classList.add('has-unread');
    if (String(c.id) === String(activeConversationId)) item.classList.add('active');
    item.style.cursor = 'pointer';
    item.dataset.conversationId = c.id;
    item.dataset.recipientId = (c.participants && c.participants[0]) ? c.participants[0].id : '';
    item.dataset.unread = c.unread || '0';
    item.innerHTML = `
      <div class="msg-avatar">👤</div>
      <div class="msg-body">
        <div class="msg-from">
          ${escapeHtml(c.participants && c.participants[0] ? c.participants[0].name : 'Conversation')}
          ${c.unread ? `<span class="msg-unread-count">${c.unread} unread</span>` : ''}
        </div>
        <div class="msg-preview">${escapeHtml((c.last_message && c.last_message.body_preview) || '')}</div>
      </div>
      <div><div class="msg-time">${c.last_message && c.last_message.sent_at ? new Date(c.last_message.sent_at).toLocaleString() : ''}</div>${c.unread ? '<div class="msg-unread-dot"></div>' : ''}</div>
    `;
    item.addEventListener('click', () => {
      const convId = item.dataset.conversationId;
      const other = item.dataset.recipientId;
      const unread = parseInt(item.dataset.unread, 10) || 0;
      setActiveConversation(convId);
      loadThread(convId, other, unread);
    });
    container.appendChild(item);
  });

  const activeItem = container.querySelector('.msg-item.active');
  if (!activeItem && list.length > 0 && document.getElementById('tab-messages')?.classList.contains('active')) {
    const first = container.querySelector('.msg-item');
    if (first) {
      first.classList.add('active');
      loadThread(first.dataset.conversationId, first.dataset.recipientId, parseInt(first.dataset.unread, 10) || 0);
    }
  }
}

function setActiveConversation(conversationId) {
  document.querySelectorAll('#conversationsList .msg-item').forEach(item => {
    item.classList.toggle('active', item.dataset.conversationId === conversationId);
  });
}

async function loadThread(conversationId, otherUserId, unreadCount = 0) {
  // Try to use message-thread API (by other_user_id) so we get messages ordered
  try {
    const r = await fetch(`/api/message-thread/${otherUserId}/`);
    if (!r.ok) throw new Error('Failed to load thread');
    const data = await r.json();
    // Populate title and composer
    document.getElementById('threadTitle').textContent = data.other_user || 'Conversation';
    document.getElementById('threadSubtitle').textContent = unreadCount ? `${unreadCount} unread message${unreadCount > 1 ? 's' : ''}` : '';
    const pane = document.getElementById('threadPane');
    pane.innerHTML = '';
    (data.messages || []).forEach(m => {
      const mdiv = document.createElement('div');
      mdiv.style.maxWidth = '85%';
      mdiv.style.padding = '.75rem 1rem';
      mdiv.style.borderRadius = m.from_me ? '12px 12px 4px 12px' : '12px 12px 12px 4px';
      mdiv.style.alignSelf = m.from_me ? 'flex-end' : 'flex-start';
      mdiv.style.background = m.from_me ? 'var(--amber)' : 'var(--cream)';
      mdiv.style.color = m.from_me ? 'white' : 'inherit';
      mdiv.innerHTML = `${escapeHtml(m.body)}<div style="font-size:.72rem;margin-top:.3rem;color:${m.from_me ? 'rgba(255,255,255,.7)' : 'var(--muted)'}">${new Date(m.sent_at).toLocaleString()}${m.from_me ? ' · You' : ''}</div>`;
      pane.appendChild(mdiv);
    });
    // set composer data attributes
    const composer = document.getElementById('threadComposer');
    if (composer) {
      composer.dataset.conversationId = data.conversation_id || conversationId || '';
      composer.dataset.recipientId = otherUserId || '';
    }
    setActiveConversation(data.conversation_id || conversationId || '');
    // refresh conversation list counts and active state after thread is read
    fetchConversations(data.conversation_id || conversationId || '');
    // scroll into view
    pane.scrollTop = pane.scrollHeight;
  } catch (err) {
    console.error('Load thread error:', err);
  }
}

function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/[&<>"]+/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;', '"':'&quot;'}[c]; });
}

// Auto-load conversations when messages tab exists
// Update message nav badge using conversations list
function updateMessageNavBadge(list) {
  const unread = (list || []).reduce((s, c) => s + (c.unread || 0), 0);
  const navBadge = document.querySelector('[data-nav="messages"] .nav-badge');
  if (navBadge) {
    navBadge.textContent = unread > 0 ? unread : '';
  }
}

let convPollInterval = null;
function startConversationsPolling(intervalMs = 15000) {
  if (convPollInterval) clearInterval(convPollInterval);
  convPollInterval = setInterval(async () => {
    try {
      const r = await fetch('/api/conversations/');
      if (!r.ok) return;
      const data = await r.json();
      const list = data.conversations || [];
      renderConversations(list);
      updateMessageNavBadge(list);
    } catch (err) {
      console.error('Conversations polling error:', err);
    }
  }, intervalMs);
}

// Auto-load conversations and start polling when messages tab exists
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('conversationsList')) {
    fetchConversations();
    startConversationsPolling(15000);
  }
});

// ──── ANIMAL CARD DATA ATTRIBUTES ────
document.addEventListener('DOMContentLoaded', () => {
  // Add animal IDs to cards for easier reference
  document.querySelectorAll('.animal-card').forEach((card, idx) => {
    // Try to extract ID from heart button or other attributes
    const heartBtn = card.querySelector('.heart-btn');
    if (heartBtn) {
      // ID should be passed via data attribute or extracted from context
      // This is a fallback pattern
    }
  });
});

// ──── ORGANIZATION DASHBOARD FUNCTIONS ────

function openReportModal(reportId, summary, status = 'pending', mode = 'respond') {
  const modal = document.getElementById('reportDetailModal');
  if (!modal) return;
  const reportIdField = modal.querySelector('#reportUpdateId');
  const reportNumber = modal.querySelector('#reportUpdateNumber');
  const reportSummary = modal.querySelector('#reportUpdateSummary');
  const statusField = modal.querySelector('#reportUpdateStatus');
  const modeText = modal.querySelector('#reportModalModeText');
  const priorityText = modal.querySelector('#reportModalPriority');
  const detailsBox = modal.querySelector('#reportModalDetails');
  const photoBox = modal.querySelector('#reportModalPhoto');
  const row = document.querySelector(`[data-report-row][data-report-id="${reportId}"]`);

  const details = row ? row.dataset : {};
  const reportStatus = details.reportStatus || status;
  const statusDisplay = details.reportStatusDisplay || status;
  const priority = details.reportPriority || 'Report Priority';
  const reporter = details.reportReporter || 'Unknown reporter';
  const location = details.reportLocation || '';
  const animal = details.reportAnimal || 'Animal';
  const condition = details.reportCondition || '';
  const date = details.reportDate || '';
  const description = details.reportDescription || summary || '';
  const notes = details.reportNotes || '';
  const photo = details.reportPhoto || '';

  if (reportIdField) reportIdField.value = reportId;
  if (reportNumber) reportNumber.textContent = reportId;
  if (reportSummary) reportSummary.textContent = `${animal}${condition ? ' · ' + condition : ''} · ${location} · Reported by ${reporter}`;
  if (statusField) statusField.value = reportStatus;
  if (modeText) modeText.textContent = mode === 'view' ? 'View' : 'Respond to';
  if (priorityText) priorityText.textContent = priority;
  if (detailsBox) {
    detailsBox.innerHTML = `
      <div><strong>Animal</strong><span>${escapeHtml(animal)}${condition ? ' · ' + escapeHtml(condition) : ''}</span></div>
      <div><strong>Reporter</strong><span>${escapeHtml(reporter)}</span></div>
      <div><strong>Status</strong><span>${escapeHtml(statusDisplay)}</span></div>
      <div><strong>Date</strong><span>${escapeHtml(date)}</span></div>
      <div class="span-2"><strong>Location</strong><span>${escapeHtml(location)}</span></div>
      <div class="span-2"><strong>Description</strong><span>${escapeHtml(description)}</span></div>
      ${notes ? `<div class="span-2"><strong>Latest org notes</strong><span>${escapeHtml(notes)}</span></div>` : ''}
    `;
  }
  if (photoBox) {
    if (photo) {
      photoBox.style.display = 'block';
      photoBox.innerHTML = `<img src="${photo}" alt="Report photo">`;
    } else {
      photoBox.style.display = 'none';
      photoBox.innerHTML = '';
    }
  }

  modal.querySelectorAll('.report-update-control').forEach(el => {
    el.style.display = mode === 'view' ? 'none' : '';
  });
  openModal('reportDetailModal');
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function submitReportUpdate(event) {
  event?.preventDefault();
  const modal = document.getElementById('reportDetailModal');
  if (!modal) return;
  const reportId = modal.querySelector('#reportUpdateId')?.value;
  const status = modal.querySelector('#reportUpdateStatus')?.value;
  const notes = modal.querySelector('#reportUpdateNotes')?.value || '';
  const photoInput = modal.querySelector('#reportUpdatePhotosInput');

  if (!reportId || !status) {
    alert('Please select a report and status.');
    return;
  }

  const fileValidation = validateReportFiles(photoInput?.files);
  if (fileValidation) {
    alert(fileValidation);
    return;
  }

  const formData = new FormData();
  formData.append('status', status);
  formData.append('response_notes', notes);
  if (photoInput) {
    Array.from(photoInput.files || []).forEach(file => formData.append('photos', file));
  }

  fetch(`/api/report/${reportId}/update/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'X-Requested-With': 'XMLHttpRequest',
      'Accept': 'application/json',
    },
    body: formData,
  })
  .then(async r => {
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Report update failed');
    return data;
  })
  .then(data => {
    if (data.ok) {
      closeModal('reportDetailModal');
      if (window.showActionFeedback) { window.showActionFeedback({ title: 'Report updated', message: 'The report status was updated successfully.' }); }
      setTimeout(() => location.reload(), 650);
    }
  })
  .catch(err => {
    console.error('Error updating report:', err);
    alert(err.message || 'Unable to update report. Please try again.');
  });
}

function submitInterestModalInquiry(event) {
  event?.preventDefault();
  const animalSelect = document.getElementById('interestModalAnimalId');
  const animalId = animalSelect?.value;
  const livingSituation = document.getElementById('interestModalLivingSituation')?.value || 'house';
  const message = document.getElementById('interestModalMessage')?.value?.trim();

  if (!animalId) {
    alert('Please select an animal before sending an inquiry.');
    return;
  }
  if (!message) {
    alert('Please enter a message for the organization.');
    return;
  }

  const formData = new FormData();
  formData.append('animal_id', animalId);
  formData.append('living_situation', livingSituation);
  formData.append('other_pets', 'none');
  formData.append('message', message);

  fetch('/api/inquiry/submit/', {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: formData,
  })
  .then(async r => {
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Inquiry submission failed');
    return data;
  })
  .then(data => {
    if (data.ok) {
      closeModal('interestModal');
      openModal('inquirySentModal');
      document.getElementById('interestModalMessage').value = '';
    }
  })
  .catch(err => {
    console.error('Error sending interest inquiry:', err);
    alert(err.message || 'Unable to send inquiry. Please try again.');
  });
}

function updateReportStatus(reportId, newStatus) {
  fetch(`/api/report/${reportId}/update/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: new URLSearchParams({
      status: newStatus,
    }),
  })
  .then(async r => {
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Report update failed');
    return data;
  })
  .then(data => {
    if (data.ok) {
      if (window.showActionFeedback) { window.showActionFeedback({ title: 'Report updated', message: 'The report status was updated successfully.' }); }
      setTimeout(() => location.reload(), 650);
    }
  })
  .catch(err => {
    console.error('Error updating report:', err);
    alert(err.message || 'Unable to update report. Please try again.');
  });
}

function markAllNotificationsRead() {
  fetch('/api/notifications/mark-read/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-CSRFToken': getCsrfToken(),
    },
    body: new URLSearchParams({ all: '1' }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.ok) {
      const unreadCount = Number.isFinite(Number(data.unread_count)) ? Number(data.unread_count) : 0;
      document.querySelectorAll('[data-notif-count]').forEach(el => { el.textContent = String(unreadCount); });
      document.querySelectorAll('.unread').forEach(el => el.classList.remove('unread'));
      document.querySelectorAll('[data-notification-id]').forEach(el => el.classList.remove('unread'));
      if (window.showActionFeedback) window.showActionFeedback({ title: 'Notifications updated', message: 'All notifications were marked as read.' });
    }
  })
  .catch(err => console.error('Error marking notifications read:', err));
}

function toggleAnimalAdoption(animalId) {
  fetch(`/api/animal/${animalId}/toggle-adoption/`, {
    method: 'POST',
    headers: {
      'X-CSRFToken': getCsrfToken(),
    },
  })
  .then(r => r.json())
  .then(data => {
    if (data.adoption_open) {
      alert('Animal is now available for adoption!');
    } else {
      alert('Animal adoption listing has been hidden');
    }
    location.reload();
  })
  .catch(err => console.error('Error toggling adoption:', err));
}

// ──── LIVE STATS UPDATES ----
function loadDashboardStats() {
  const profile = document.body.dataset.userRole || 'user';
  
  if (profile === 'admin' || profile === 'rescue_org') {
    const statsUrl = profile === 'admin' 
      ? '/api/dashboard-stats/' 
      : '/api/org-stats/';
    
    fetch(statsUrl)
      .then(r => r.json())
      .then(data => {
        // Update stat cards if they exist
        const statCards = document.querySelectorAll('.stat-value');
        if (statCards.length > 0 && data) {
          // Update first 4 cards with available data
          const values = [
            data.total_reports || data.monthly_data?.[5]?.reports || 0,
            data.pending_rescues || data.monthly_data?.[5]?.rescued || 0,
            data.rescued_animals || 0,
            data.ready_for_adoption || 0,
          ];
          statCards.forEach((card, idx) => {
            if (values[idx]) card.textContent = values[idx];
          });
        }
      })
      .catch(err => console.error('Error loading stats:', err));
  }
}

// Update stats on page load
document.addEventListener('DOMContentLoaded', () => {
  loadDashboardStats();
  initBrowseFilterHandlers();
  initOrgReportFilters();
  initOrgAnimalFilters();
  applyBrowseFilters();
  applyOrgReportFilters();
  applyOrgAnimalFilters();
  initReportMap();
  initPhotoPreview();
  // Refresh stats every 2 minutes
  setInterval(loadDashboardStats, 120000);
});

// ──── RESPONSIVE SIDEBAR ────
window.addEventListener('resize', () => {
  if (window.innerWidth > 768) {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.classList.remove('open');
    }
  }
});

// Global action feedback modal for user and organization dashboards.
(function initActionFeedbackModal() {
  function ensureModal() {
    let overlay = document.getElementById('actionFeedbackModal');
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.id = 'actionFeedbackModal';
    overlay.className = 'action-feedback-overlay';
    overlay.innerHTML = `
      <div class="action-feedback-modal" role="dialog" aria-modal="true" aria-labelledby="actionFeedbackTitle">
        <div class="action-feedback-icon" id="actionFeedbackIcon">✨</div>
        <h3 class="action-feedback-title" id="actionFeedbackTitle">Confirm action</h3>
        <p class="action-feedback-message" id="actionFeedbackMessage">Please confirm this action.</p>
        <div class="action-feedback-actions">
          <button type="button" class="action-feedback-btn action-feedback-cancel" id="actionFeedbackCancel">Cancel</button>
          <button type="button" class="action-feedback-btn action-feedback-confirm" id="actionFeedbackConfirm">Continue</button>
          <button type="button" class="action-feedback-btn action-feedback-confirm action-feedback-close" id="actionFeedbackClose">Got it</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    return overlay;
  }

  function setModal({ mode = 'confirm', icon = '✨', title = 'Confirm action', message = 'Please confirm this action.', confirmText = 'Continue', onConfirm = null }) {
    const overlay = ensureModal();
    overlay.classList.remove('is-notice', 'is-processing');
    if (mode === 'notice') overlay.classList.add('is-notice');
    if (mode === 'processing') overlay.classList.add('is-processing');
    overlay.querySelector('#actionFeedbackIcon').textContent = icon;
    overlay.querySelector('#actionFeedbackTitle').textContent = title;
    overlay.querySelector('#actionFeedbackMessage').textContent = message;
    overlay.querySelector('#actionFeedbackConfirm').textContent = confirmText;
    overlay.classList.add('show');

    const cancel = overlay.querySelector('#actionFeedbackCancel');
    const close = overlay.querySelector('#actionFeedbackClose');
    const confirm = overlay.querySelector('#actionFeedbackConfirm');
    const hide = () => overlay.classList.remove('show');
    cancel.onclick = hide;
    close.onclick = hide;
    confirm.onclick = () => {
      if (onConfirm) onConfirm();
      else hide();
    };
    overlay.onclick = (event) => {
      if (event.target === overlay && mode !== 'processing') hide();
    };
  }

  window.showActionFeedback = function showActionFeedback(options) {
    setModal({ mode: 'notice', icon: '✅', title: 'Done', message: 'Action completed successfully.', ...options });
  };
  window.showActionProcessing = function showActionProcessing(options) {
    setModal({ mode: 'processing', icon: '', title: 'Working...', message: 'Please wait while the system processes your request.', ...options });
  };
  window.confirmActionFeedback = function confirmActionFeedback(options) {
    setModal({ mode: 'confirm', ...options });
  };

  document.addEventListener('DOMContentLoaded', () => {
    ensureModal();

    document.querySelectorAll('[data-flash-message]').forEach(el => {
      const tags = (el.dataset.flashTags || '').toLowerCase();
      const isError = tags.includes('error') || tags.includes('danger');
      window.showActionFeedback({
        icon: isError ? '⚠️' : '✅',
        title: isError ? 'Action needed' : 'Action completed',
        message: el.dataset.flashMessage || el.textContent.trim() || 'Action completed.'
      });
    });

    document.addEventListener('submit', (event) => {
      const form = event.target;
      if (!(form instanceof HTMLFormElement)) return;
      if (form.dataset.skipActionModal === 'true') return;
      if (form.dataset.actionConfirmed === 'true') return;
      const method = (form.method || 'get').toLowerCase();
      if (method !== 'post') return;

      const submitter = event.submitter;
      const actionText = form.dataset.actionName || submitter?.textContent?.trim() || 'Save changes';
      const lower = actionText.toLowerCase();
      const isDestructive = lower.includes('deactivate') || lower.includes('archive') || lower.includes('delete') || lower.includes('remove');
      event.preventDefault();
      window.confirmActionFeedback({
        icon: isDestructive ? '⚠️' : '✨',
        title: form.dataset.confirmTitle || `${actionText}?`,
        message: form.dataset.confirmMessage || 'This will apply your changes. Continue?',
        confirmText: form.dataset.confirmText || actionText,
        onConfirm: () => {
          form.dataset.actionConfirmed = 'true';
          window.showActionProcessing({ title: 'Processing action', message: 'Saving your changes...' });
          form.submit();
        }
      });
    });

    document.addEventListener('click', (event) => {
      const link = event.target.closest('a');
      if (!link || link.dataset.skipActionModal === 'true') return;
      const text = link.textContent.trim().toLowerCase();
      const href = link.getAttribute('href') || '';
      if (!text.includes('export') && !href.toLowerCase().includes('export')) return;
      event.preventDefault();
      window.confirmActionFeedback({
        icon: '📄',
        title: 'Export CSV?',
        message: 'The system will generate and download the CSV file.',
        confirmText: 'Export',
        onConfirm: () => {
          window.showActionProcessing({ title: 'Preparing export', message: 'Your CSV download should start shortly.' });
          const iframe = document.createElement('iframe');
          iframe.style.display = 'none';
          iframe.src = link.href;
          document.body.appendChild(iframe);
          setTimeout(() => {
            window.showActionFeedback({ icon: '✅', title: 'Export ready', message: 'Your CSV download has started.' });
            setTimeout(() => iframe.remove(), 4000);
          }, 1200);
        }
      });
    });
  });
})();

// Incremental real-data rescue tracking refresh for reporter dashboard.
document.addEventListener('DOMContentLoaded', () => {
  if (document.body?.dataset?.userRole !== 'reporter') return;
  const trackingTab = document.getElementById('tab-tracking');
  if (!trackingTab) return;
  setInterval(() => {
    if (trackingTab.classList.contains('active')) {
      window.location.reload();
    }
  }, 30000);
});


// ──── PHASE 3.1: org inquiry list/thread toggles, animal view toggle, report update photo preview ────
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-open-inquiry]').forEach(button => {
    button.addEventListener('click', () => {
      const id = button.dataset.openInquiry;
      document.querySelectorAll('[data-open-inquiry]').forEach(item => item.classList.toggle('active', item === button));
      document.querySelectorAll('[data-inquiry-panel]').forEach(panel => panel.classList.toggle('active', panel.dataset.inquiryPanel === id));
    });
  });

  const animalGrid = document.querySelector('.animal-grid');
  document.querySelectorAll('[data-animal-view]').forEach(button => {
    button.addEventListener('click', () => {
      const view = button.dataset.animalView;
      if (animalGrid) animalGrid.classList.toggle('list-view', view === 'list');
      document.querySelectorAll('[data-animal-view]').forEach(item => {
        item.classList.toggle('btn-primary', item === button);
        item.classList.toggle('btn-outline', item !== button);
      });
    });
  });

  const updateInput = document.getElementById('reportUpdatePhotosInput');
  const updatePreview = document.getElementById('reportUpdatePreview');
  if (updateInput && updatePreview) {
    const renderUpdatePreview = () => {
      const files = Array.from(updateInput.files || []);
      updatePreview.innerHTML = '';
      updatePreview.style.display = files.length ? 'flex' : 'none';
      files.slice(0, 5).forEach(file => {
        const item = document.createElement('div');
        item.className = 'preview-item';
        item.innerHTML = `<img src="${URL.createObjectURL(file)}" alt="Rescue photo preview">`;
        updatePreview.appendChild(item);
      });
    };
    updateInput.addEventListener('change', renderUpdatePreview);
  }
});

// Phase 3.4: user adoption inquiry list -> selected thread behavior.
document.addEventListener('click', (event) => {
  const trigger = event.target.closest('[data-open-user-inquiry]');
  if (!trigger) return;
  event.preventDefault();
  const inquiryId = trigger.getAttribute('data-open-user-inquiry');
  if (!inquiryId) return;
  document.querySelectorAll('[data-open-user-inquiry]').forEach(item => {
    const active = item === trigger;
    item.classList.toggle('active', active);
    item.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  document.querySelectorAll('[data-user-inquiry-panel]').forEach(panel => {
    const active = panel.getAttribute('data-user-inquiry-panel') === inquiryId;
    panel.classList.toggle('active', active);
    panel.hidden = !active;
  });
});

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-user-inquiry-panel]').forEach(panel => {
    panel.hidden = !panel.classList.contains('active');
  });
});
