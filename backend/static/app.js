// AdultMoney Web PWA Dashboard Logic

// Authored SVG Icons Registry (Impeccable Design Standard: No raw emojis for UI icons)
const SVG_ICONS = {
  trip: `<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 6V4a2 2 0 012-2h2a2 2 0 012 2v2m4 0H5a2 2 0 00-2 2v11a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2zM9 12v4m6-4v4"/></svg>`,
  tag: `<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/></svg>`,
  flight: `<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/></svg>`,
  drive: `<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M5 17h14M5 17a2 2 0 01-2-2V9a2 2 0 012-2h14a2 2 0 012 2v6a2 2 0 01-2 2M5 17l1 3h12l1-3M7 13h.01M17 13h.01"/></svg>`,
  briefcase: `<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/></svg>`,
  home: `<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 12l9-9 9 9M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/></svg>`,
  calendar: `<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
  plus: `<svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>`,
  close: `<svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg>`,
  trash: `<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>`,
  edit: `<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>`,
  split: `<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/></svg>`,
  location: `<svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>`
};

function getTagSvg(iconKey, size = 13) {
  if (!iconKey || !SVG_ICONS[iconKey]) {
    const map = {
      '🏖️': 'trip',
      '✈️': 'flight',
      '🚗': 'drive',
      '💼': 'briefcase',
      '🏷️': 'tag'
    };
    iconKey = map[iconKey] || 'tag';
  }
  const svg = SVG_ICONS[iconKey] || SVG_ICONS.tag;
  if (size === 14) return svg;
  return svg.replace(/width="\d+" height="\d+"/, `width="${size}" height="${size}"`);
}

document.addEventListener('DOMContentLoaded', () => {
  initAppTitle();
  loadCategoryCatalog();
  loadSummaryStats();
  checkActiveTripBanner();
  populateTagFilter();
  loadRecentTransactions();
  loadUnreviewedQueue();
  setupDragAndDrop();

  handleHashRouting();
  window.addEventListener('hashchange', handleHashRouting);

  // Non-modal Popover & Panel dismissal handlers
  window.addEventListener('click', (e) => {
    const popover = document.getElementById('tagPopover');
    if (popover && popover.style.display !== 'none') {
      if (!popover.contains(e.target) && !e.target.closest('.btn-tag-action')) {
        closeTagPopover();
      }
    }
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeTagPopover();
      toggleTripCreatorPanel(false);
    }
  });
});

function handleHashRouting() {
  const rawHash = (window.location.hash || '#dashboard').replace('#', '').trim();
  const validSections = ['dashboard', 'transactions', 'review', 'budgets', 'analytics', 'upload', 'tags'];
  const targetSection = validSections.includes(rawHash) ? rawHash : 'dashboard';
  showSection(targetSection);
}


function initAppTitle() {
  const title = (window.APP_CONFIG && window.APP_CONFIG.APP_TITLE) ? window.APP_CONFIG.APP_TITLE : "AdultMoney";
  document.title = `${title} — Personal Expense Intelligence`;
  const brandEl = document.getElementById('brandTitle');
  if (brandEl) brandEl.textContent = title;
}

let searchTimer = null;
function debounceSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    loadFullTransactions();
  }, 300);
}

function showSection(sectionId) {
  const sections = ['sectionDashboard', 'sectionTransactions', 'sectionReview', 'sectionBudgets', 'sectionAnalytics', 'sectionTags'];
  const titleMap = {
    'dashboard': 'Dashboard',
    'transactions': 'All Transactions',
    'analytics': 'Monthly Analytics & Category Trends',
    'budgets': 'Budgets & Custom Rules',
    'review': '1-Tap Ambiguity Review Queue',
    'upload': 'Statement Import',
    'tags': 'Trips & Expense Tags'
  };

  document.getElementById('pageTitle').textContent = titleMap[sectionId] || 'Dashboard';

  sections.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      if (sectionId === 'upload' && id === 'sectionDashboard') {
        el.style.display = 'grid';
      } else {
        const matches = (id === 'section' + sectionId.charAt(0).toUpperCase() + sectionId.slice(1));
        el.style.display = matches ? (id === 'sectionDashboard' || id === 'sectionBudgets' ? 'grid' : 'flex') : 'none';
      }
    }
  });

  // Update nav highlight
  document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
  document.querySelectorAll('.mobile-nav-item').forEach(item => item.classList.remove('active'));

  const mobItem = document.getElementById(`mobNav${sectionId.charAt(0).toUpperCase() + sectionId.slice(1)}`);
  if (mobItem) mobItem.classList.add('active');

  if (sectionId === 'transactions') {
    loadFullTransactions();
  } else if (sectionId === 'tags') {
    loadTripsAndTags();
  } else if (sectionId === 'review') {
    loadUnreviewedQueue();
  } else if (sectionId === 'budgets') {
    loadBudgets();
    loadMerchantRules();
  } else if (sectionId === 'analytics') {
    loadAnalyticsTrends();
  }
}

async function loadSummaryStats() {
  try {
    let res = await fetch('/api/v1/transactions/summary');
    if (!res.ok) {
      res = await fetch('/api/v1/transactions/stats/summary');
    }
    if (!res.ok) {
      console.warn('Failed to fetch summary stats, status:', res.status);
      return;
    }
    const data = await res.json();

    // Update Title if returned from API
    if (data.app_title) {
      const brandEl = document.getElementById('brandTitle');
      if (brandEl) brandEl.textContent = data.app_title;
    }

    // Total Spend
    const totalFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(data.total_spend_inr);
    document.getElementById('valTotalSpend').textContent = totalFormatted;

    // Budget Progress (Default 1.8L)
    const budgetTotal = (window.APP_CONFIG && window.APP_CONFIG.DEFAULT_BUDGET_INR) ? window.APP_CONFIG.DEFAULT_BUDGET_INR : 180000;
    const remaining = Math.max(0, budgetTotal - data.total_spend_inr);
    const pct = Math.min(100, (data.total_spend_inr / budgetTotal) * 100);

    const remainingFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(remaining);
    const spentFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(data.total_spend_inr);
    const budgetFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(budgetTotal);

    document.getElementById('valBudgetRemaining').textContent = `${remainingFormatted} left`;
    document.getElementById('valBudgetLabel').textContent = `${spentFormatted} / ${budgetFormatted}`;
    document.getElementById('progressBudgetFill').style.width = `${pct}%`;

    // Net Receivables
    const recFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(data.net_receivables_inr || 0);
    const recEl = document.getElementById('valNetReceivables');
    if (recEl) recEl.textContent = recFormatted;

    // Unreviewed Counter
    const unreviewedEl = document.getElementById('valUnreviewedCount');
    const badgeEl = document.getElementById('sidebarReviewCount');
    unreviewedEl.textContent = data.unreviewed_count;
    
    if (data.unreviewed_count > 0) {
      badgeEl.textContent = data.unreviewed_count;
      badgeEl.style.display = 'inline-flex';
    } else {
      badgeEl.style.display = 'none';
    }

    // Category Breakdown List
    renderCategoryBreakdown(data.category_breakdown);

    // Issuer Breakdown List
    renderIssuerBreakdown(data.issuer_breakdown);

  } catch (err) {
    console.error('Failed loading stats:', err);
    const catContainer = document.getElementById('categoryBreakdownList');
    if (catContainer) {
      catContainer.innerHTML = `<div style="color:var(--accent-warning); padding:12px; font-size:12px;">⚠️ Unable to connect to server API. If using an AdBlocker (e.g. uBlock/Ghostery), try disabling it for localhost or access via <a href="http://192.168.68.120:8000" style="color:white;">http://192.168.68.120:8000</a></div>`;
    }
  }
}

function renderCategoryBreakdown(items) {
  const container = document.getElementById('categoryBreakdownList');
  if (!items || items.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); padding:12px;">No categorized expenses yet.</div>`;
    return;
  }

  container.innerHTML = items.slice(0, 6).map(cat => {
    const formatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(cat.amount_inr);
    return `
      <div class="category-spend-row">
        <div class="category-header">
          <span class="category-name" title="${escapeHtml(cat.category)}">${escapeHtml(cat.category)}</span>
          <span class="category-amount">${formatted} <span class="category-pct">(${cat.percentage}%)</span></span>
        </div>
        <div class="progress-track" style="height:4px; margin-top:0;">
          <div class="progress-fill" style="width: ${cat.percentage}%;"></div>
        </div>
      </div>
    `;
  }).join('');
}

function renderIssuerBreakdown(items) {
  const container = document.getElementById('issuerBreakdownList');
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); padding:12px;">No card data available.</div>`;
    return;
  }

  // Dynamically populate issuer filter dropdown options
  const issuerSelect = document.getElementById('issuerFilter');
  if (issuerSelect) {
    const currentVal = issuerSelect.value;
    issuerSelect.innerHTML = `<option value="">All Issuers / Banks</option>` + items.map(i => `<option value="${escapeHtml(i.issuer)}">${escapeHtml(i.issuer)}</option>`).join('');
    if (currentVal) issuerSelect.value = currentVal;
  }

  container.innerHTML = items.map(iss => {
    const formatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(iss.amount_inr);
    return `
      <div onclick="filterByIssuer('${escapeHtml(iss.issuer)}')" class="issuer-clickable-row" style="display:flex; justify-content:space-between; align-items:center; padding:8px 10px; border-bottom:1px solid var(--border-subtle); cursor:pointer; border-radius:var(--radius-sm); transition:background 0.15s ease;" title="Click to view all ${escapeHtml(iss.issuer)} transactions">
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="issuer-badge">${escapeHtml(iss.issuer)}</span>
          <span style="font-size:12px; color:var(--text-muted);">${iss.count} txn${iss.count > 1 ? 's' : ''}</span>
        </div>
        <div style="display:flex; align-items:center; gap:6px;">
          <span style="font-family:var(--font-mono); font-weight:600; color:var(--text-primary);">${formatted}</span>
          <span style="font-size:12px; color:var(--text-muted);">→</span>
        </div>
      </div>
    `;
  }).join('');
}

function filterByIssuer(issuerName) {
  const issuerSelect = document.getElementById('issuerFilter');
  if (issuerSelect) {
    issuerSelect.value = issuerName;
  }
  showSection('transactions');
  loadFullTransactions();
}

async function loadRecentTransactions() {
  try {
    const res = await fetch('/api/v1/transactions?limit=8');
    if (!res.ok) return;
    const items = await res.json();

    const tbody = document.getElementById('recentTransactionsTable');
    const mobileList = document.getElementById('recentTransactionsMobile');

    if (!items || items.length === 0) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:24px;">No transactions recorded. Sync from phone app or upload statement.</td></tr>`;
      if (mobileList) mobileList.innerHTML = `<div style="text-align:center; color:var(--text-muted); padding:24px;">No transactions recorded.</div>`;
      return;
    }

    if (tbody) tbody.innerHTML = items.map(t => renderTransactionRow(t, false)).join('');
    if (mobileList) mobileList.innerHTML = items.map(t => renderMobileTransactionCard(t)).join('');
  } catch (err) {
    console.error('Failed loading recent transactions:', err);
  }
}

async function loadFullTransactions() {
  const search = document.getElementById('searchInput').value;
  const category = document.getElementById('categoryFilter').value;
  const issuerSelect = document.getElementById('issuerFilter');
  const issuer = issuerSelect ? issuerSelect.value : '';
  const tagSelect = document.getElementById('tagFilter');
  const tag = tagSelect ? tagSelect.value : '';

  let url = `/api/v1/transactions?limit=100`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (category) url += `&category=${encodeURIComponent(category)}`;
  if (issuer) url += `&issuer=${encodeURIComponent(issuer)}`;
  if (tag) url += `&tag=${encodeURIComponent(tag)}`;


  try {
    const res = await fetch(url);
    if (!res.ok) return;
    const items = await res.json();

    const tbody = document.getElementById('fullTransactionsTable');
    const mobileList = document.getElementById('fullTransactionsMobile');

    if (!items || items.length === 0) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:24px;">No matching transactions found.</td></tr>`;
      if (mobileList) mobileList.innerHTML = `<div style="text-align:center; color:var(--text-muted); padding:24px;">No matching transactions found.</div>`;
      return;
    }

    if (tbody) tbody.innerHTML = items.map(t => renderTransactionRow(t, true)).join('');
    if (mobileList) mobileList.innerHTML = items.map(t => renderMobileTransactionCard(t)).join('');
  } catch (err) {
    console.error('Failed loading full transactions:', err);
  }
}

function renderTransactionRow(t, showAction) {
  const merchant = t.merchant_clean || t.merchant_raw || 'Transaction';
  const totalAmountFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.amount_inr);
  const dateFormatted = t.transacted_at_utc ? new Date(t.transacted_at_utc).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' }) : '';
  const categoryStr = t.category || 'Uncategorized';
  const issuerStr = t.issuer || 'Bank';

  let locationBadgeHtml = t.location_name 
    ? `<div style="font-size:11px; color:var(--text-secondary); margin-top:2px; display:flex; align-items:center; gap:4px;"><span style="color:var(--accent-warning); display:inline-flex; align-items:center;">${SVG_ICONS.location}</span> ${escapeHtml(t.location_name)}</div>`
    : '';

  const nonSplittable = ['Transfers & Payments', 'Transfers', 'Transfer', 'Rewards & Cashback'];
  const isCredit = t.transaction_type === 'credit';
  const isEligibleCategory = !nonSplittable.includes(categoryStr);
  const isSplittable = !isCredit && isEligibleCategory && (t.amount_inr > 0);

  // Smart Heuristic Classifier for high-likelihood split candidate expenses
  const amt = t.amount_inr || 0;
  const catLower = categoryStr.toLowerCase();
  let isHighLikelihoodSplit = false;

  if (catLower.includes('food') || catLower.includes('dining') || catLower.includes('restaurant') || catLower.includes('cafe')) {
    if (amt >= 350) isHighLikelihoodSplit = true; // Dining >= Rs 350
  } else if (catLower.includes('travel') || catLower.includes('entertainment') || catLower.includes('movie') || catLower.includes('hotel')) {
    if (amt >= 500) isHighLikelihoodSplit = true; // Travel / Events / Outings >= Rs 500
  } else if (catLower.includes('grocery') || catLower.includes('shopping')) {
    if (amt >= 1000) isHighLikelihoodSplit = true; // Shared Groceries / Shopping >= Rs 1000
  }

  let splitBadgeHtml = '';
  if (t.is_split) {
    const myShareFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.my_share_inr);
    const recFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.reimbursable_inr);
    splitBadgeHtml = `
      <div style="font-size:11px; color:var(--accent-primary); margin-top:3px; display:inline-flex; align-items:center; gap:6px; background:rgba(59, 130, 246, 0.08); padding:2px 8px; border-radius:4px; border:1px solid rgba(59, 130, 246, 0.18);">
        <span style="display:inline-flex; align-items:center; gap:4px;">${SVG_ICONS.split} Split (${t.split_ratio_label}): My Share ${myShareFormatted} • Owed ${recFormatted}</span>
        <button onclick="unsplitTransaction(${t.id})" style="background:none; border:none; color:var(--accent-danger); cursor:pointer; font-size:11px; font-weight:600; padding:0 2px;" title="Cancel Split">✕</button>
      </div>
    `;
  } else if (isSplittable) {
    splitBadgeHtml = `
      <div id="splitChips_${t.id}" style="display:none; align-items:center; gap:3px; margin-top:3px;">
        <span style="font-size:10px; font-weight:600; color:var(--text-muted); letter-spacing:0.03em;">SPLIT:</span>
        <button onclick="splitTransactionPreset(${t.id}, '1/2', ${t.amount_inr})" class="btn-icon" style="height:18px; padding:0 5px; font-size:10px; border-radius:3px;" title="Split 50/50">½</button>
        <button onclick="splitTransactionPreset(${t.id}, '1/3', ${t.amount_inr})" class="btn-icon" style="height:18px; padding:0 5px; font-size:10px; border-radius:3px;" title="Split 1/3">⅓</button>
        <button onclick="promptCustomSplit(${t.id}, ${t.amount_inr})" class="btn-icon" style="height:18px; padding:0 5px; font-size:10px; border-radius:3px;" title="Custom Share">✎</button>
      </div>
    `;
  }

  // Tags pill HTML (Impeccable standard: Author-styled SVG tag pills & inline non-modal popover trigger)
  let tagsHtml = '<div style="display:flex; flex-wrap:wrap; align-items:center; gap:4px; margin-top:4px;">';
  const tagList = (t.tag_details && t.tag_details.length > 0)
    ? t.tag_details
    : (t.tags || []).map(name => {
        const found = (allTagsCache || []).find(tg => tg.name.toLowerCase() === name.toLowerCase());
        return found ? { id: found.id, name: found.name, color: found.color, icon: found.icon } : { id: name, name: name, color: '#6366F1', icon: 'tag' };
      });

  tagList.forEach(tg => {
    const tagIdentifier = tg.id !== undefined && tg.id !== null ? tg.id : tg.name;
    tagsHtml += `
      <span class="tag-pill" style="border-color:${tg.color || '#6366F1'};" title="Tag: ${escapeHtml(tg.name)}">
        <span style="display:inline-flex; align-items:center; color:${tg.color || '#6366F1'};">${getTagSvg(tg.icon, 11)}</span>
        <span>${escapeHtml(tg.name)}</span>
        <button onclick="removeTagFromTxn(${t.id}, '${escapeHtml(String(tagIdentifier))}', event)" class="tag-pill-remove" title="Remove tag">${SVG_ICONS.close}</button>
      </span>
    `;
  });
  tagsHtml += `<button class="btn-tag-action" onclick="toggleTagPopover(event, ${t.id})" title="Attach Tag">${SVG_ICONS.plus} Tag</button></div>`;

  let actionButtonsHtml = '';
  if (isSplittable && !t.is_split) {
    actionButtonsHtml += `<button class="btn-icon-only" style="width:28px; height:28px; border-radius:4px; padding:0; display:inline-flex; align-items:center; justify-content:center; border:1px solid var(--border-subtle); background:var(--bg-app); cursor:pointer;" onclick="toggleTxnSplitControls(${t.id})" title="Split Expense">${SVG_ICONS.split}</button>`;
  }
  if (showAction) {
    actionButtonsHtml += `<button class="btn-icon-only" style="width:28px; height:28px; margin-left:4px;" onclick="dismissTxnDirect(${t.id})" title="Dismiss as Non-Expense"><svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>`;
  }

  return `
    <tr>
      <td class="merchant-cell">
        ${escapeHtml(merchant)}
        ${locationBadgeHtml}
        ${splitBadgeHtml}
        ${tagsHtml}
      </td>
      <td><span class="chip" style="min-height:26px; padding:2px 8px; font-size:11px; margin:0; display:inline-flex; align-items:center;">${escapeHtml(categoryStr)}</span></td>
      <td><span class="issuer-badge">${escapeHtml(issuerStr)}</span></td>
      <td style="font-size:12px; color:var(--text-muted);">${dateFormatted}</td>
      <td class="amount-text">${totalAmountFormatted}</td>
      <td>${actionButtonsHtml}</td>
    </tr>
  `;
}

function renderMobileTransactionCard(t) {
  const merchant = t.merchant_clean || t.merchant_raw || 'Transaction';
  const amountFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.amount_inr);
  const dateFormatted = t.transacted_at_utc ? new Date(t.transacted_at_utc).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }) : '';
  const categoryStr = t.category || 'Uncategorized';
  const issuerStr = t.issuer || 'Bank';

  let locationBadgeHtml = t.location_name 
    ? `<div style="font-size:11px; color:var(--text-secondary); margin-top:2px; display:flex; align-items:center; gap:4px;"><span style="color:var(--accent-warning); display:inline-flex; align-items:center;">${SVG_ICONS.location}</span> ${escapeHtml(t.location_name)}</div>`
    : '';

  const nonSplittable = ['Transfers & Payments', 'Transfers', 'Transfer', 'Rewards & Cashback'];
  const isCredit = t.transaction_type === 'credit';
  const isEligibleCategory = !nonSplittable.includes(categoryStr);
  const isSplittable = !isCredit && isEligibleCategory && (t.amount_inr > 0);

  let splitControlsHtml = '';
  if (t.is_split) {
    const myShareFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.my_share_inr);
    const recFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.reimbursable_inr);
    splitControlsHtml = `
      <div style="font-size:11px; color:var(--accent-primary); margin-top:6px; display:flex; justify-content:space-between; align-items:center; background:rgba(59, 130, 246, 0.08); padding:4px 8px; border-radius:var(--radius-sm); border:1px solid rgba(59, 130, 246, 0.18);">
        <span style="display:inline-flex; align-items:center; gap:4px;">${SVG_ICONS.split} Split: My Share ${myShareFormatted} | Owed ${recFormatted}</span>
        <button onclick="unsplitTransaction(${t.id})" style="background:none; border:none; color:var(--accent-danger); cursor:pointer; font-size:11px; font-weight:600;">✕ Unsplit</button>
      </div>
    `;
  } else if (isSplittable) {
    splitControlsHtml = `
      <div id="splitChips_mob_${t.id}" style="display:none; align-items:center; gap:6px; margin-top:6px;">
        <span style="font-size:11px; color:var(--text-muted);">Split:</span>
        <button onclick="splitTransactionPreset(${t.id}, '1/2', ${t.amount_inr})" class="chip" style="min-height:22px; padding:2px 8px; font-size:10px;">½ Split</button>
        <button onclick="splitTransactionPreset(${t.id}, '1/3', ${t.amount_inr})" class="chip" style="min-height:22px; padding:2px 8px; font-size:10px;">⅓ Split</button>
        <button onclick="promptCustomSplit(${t.id}, ${t.amount_inr})" class="chip" style="min-height:22px; padding:2px 8px; font-size:10px;">Custom Share</button>
      </div>
    `;
  }

  const mobScissorBtn = (isSplittable && !t.is_split)
    ? `<button style="background:none; border:none; cursor:pointer; padding:0 4px; display:inline-flex; align-items:center;" onclick="toggleTxnSplitControls(${t.id})" title="Split Expense">${SVG_ICONS.split}</button>`
    : '';

  let mobTagsHtml = '<div style="display:flex; flex-wrap:wrap; align-items:center; gap:4px; margin-top:4px;">';
  const mobTagList = (t.tag_details && t.tag_details.length > 0)
    ? t.tag_details
    : (t.tags || []).map(name => {
        const found = (allTagsCache || []).find(tg => tg.name.toLowerCase() === name.toLowerCase());
        return found ? { id: found.id, name: found.name, color: found.color, icon: found.icon } : { id: name, name: name, color: '#6366F1', icon: 'tag' };
      });

  mobTagList.forEach(tg => {
    const tagIdentifier = tg.id !== undefined && tg.id !== null ? tg.id : tg.name;
    mobTagsHtml += `
      <span class="tag-pill" style="border-color:${tg.color || '#6366F1'}; font-size:10px; padding:1px 5px;" title="Tag: ${escapeHtml(tg.name)}">
        <span style="display:inline-flex; align-items:center; color:${tg.color || '#6366F1'};">${getTagSvg(tg.icon, 10)}</span>
        <span>${escapeHtml(tg.name)}</span>
        <button onclick="removeTagFromTxn(${t.id}, '${escapeHtml(String(tagIdentifier))}', event)" class="tag-pill-remove" title="Remove tag">${SVG_ICONS.close}</button>
      </span>
    `;
  });
  mobTagsHtml += `<button class="btn-tag-action" style="font-size:10px; padding:1px 5px;" onclick="toggleTagPopover(event, ${t.id})" title="Attach Tag">${SVG_ICONS.plus} Tag</button></div>`;

  return `
    <div class="mobile-txn-card">
      <div class="mobile-txn-top">
        <span class="mobile-txn-merchant">
          ${escapeHtml(merchant)}
          ${locationBadgeHtml}
        </span>
        <span class="mobile-txn-amount">${amountFormatted}</span>
      </div>
      <div class="mobile-txn-bottom">
        <div class="mobile-txn-tags">
          <span class="chip" style="min-height:24px; padding:2px 8px; font-size:11px;">${escapeHtml(categoryStr)}</span>
          <span class="issuer-badge">${escapeHtml(issuerStr)}</span>
          ${mobScissorBtn}
        </div>
        <span>${dateFormatted}</span>
      </div>
      ${mobTagsHtml}
      ${splitControlsHtml}
    </div>
  `;

}

async function loadUnreviewedQueue() {
  try {
    const res = await fetch('/api/v1/categories/unreviewed');
    if (!res.ok) return;
    const items = await res.json();

    const container = document.getElementById('unreviewedCardsContainer');
    const badge = document.getElementById('reviewQueueBadge');

    badge.textContent = `${items.length} Pending`;

    if (!items || items.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:40px; color:var(--text-muted); background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:var(--radius-lg);">
          <div style="font-size:32px; margin-bottom:8px;">🎉</div>
          <div style="font-weight:600; color:var(--text-primary);">All Caught Up!</div>
          <div style="font-size:12px; margin-top:4px;">No transactions currently require manual review.</div>
        </div>
      `;
      return;
    }

    container.innerHTML = items.map(t => {
      const merchant = t.merchant_clean || t.merchant_raw || 'Unknown Merchant';
      const amountFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.amount_inr);
      const rawText = t.raw_body ? t.raw_body : '';

      let splitNotice = '';
      if (t.is_split) {
        splitNotice = `<div style="font-size:11px; color:var(--accent-primary); font-weight:600; margin-top:4px; display:inline-flex; align-items:center; gap:4px;">${SVG_ICONS.split} Split Active: My Share ₹${t.my_share_inr} | Owed ₹${t.reimbursable_inr}</div>`;
      }

      return `
        <div class="panel" id="reviewCard_${t.id}">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="font-weight:700; font-size:16px; color:var(--text-primary);">${escapeHtml(merchant)}</div>
              <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">${escapeHtml(t.issuer)} • ${t.card_type}</div>
              ${splitNotice}
            </div>
            <div style="display:flex; align-items:center; gap:12px;">
              <span style="font-family:var(--font-mono); font-weight:700; font-size:18px; color:var(--accent-primary);">${amountFormatted}</span>
              <button class="btn-icon-only" onclick="dismissUnreviewed(${t.id})" title="Dismiss as Non-Expense">
                <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </div>

          ${rawText ? `<div style="font-size:12px; background:var(--bg-app); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:10px; color:var(--text-secondary); line-height:1.4;">${escapeHtml(rawText)}</div>` : ''}

          <div style="display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:8px; margin-top:4px;">
            <div style="display:flex; flex-wrap:wrap; gap:6px;">
              <button class="chip" onclick="categorizeUnreviewed(${t.id}, 'Dining')">Dining</button>
              <button class="chip" onclick="categorizeUnreviewed(${t.id}, 'Groceries')">Groceries</button>
              <button class="chip" onclick="categorizeUnreviewed(${t.id}, 'Shopping')">Shopping</button>
              <button class="chip" onclick="categorizeUnreviewed(${t.id}, 'Travel')">Travel</button>
              <button class="chip" onclick="categorizeUnreviewed(${t.id}, 'Fuel')">Fuel</button>
            </div>
            
            <div style="display:flex; align-items:center; gap:4px; margin-left:auto;">
              <span style="font-size:11px; color:var(--text-muted);">Split:</span>
              <button onclick="splitTransactionPreset(${t.id}, '1/2', ${t.amount_inr})" class="chip" style="min-height:24px; padding:2px 8px; font-size:11px; border-color:var(--accent-primary); color:var(--accent-primary);">½ (50%)</button>
              <button onclick="splitTransactionPreset(${t.id}, '1/3', ${t.amount_inr})" class="chip" style="min-height:24px; padding:2px 8px; font-size:11px; border-color:var(--accent-primary); color:var(--accent-primary);">⅓ (33%)</button>
              <button onclick="promptCustomSplit(${t.id}, ${t.amount_inr})" class="chip" style="min-height:24px; padding:2px 8px; font-size:11px;">Custom</button>
            </div>
          </div>
        </div>
      `;
    }).join('');

  } catch (err) {
    console.error('Failed loading unreviewed queue:', err);
  }
}

async function categorizeUnreviewed(txnId, category) {
  const card = document.getElementById(`reviewCard_${txnId}`);
  if (card) card.remove();

  try {
    const res = await fetch(`/api/v1/categories/${txnId}/categorize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category })
    });
    if (res.ok) {
      loadSummaryStats();
      loadRecentTransactions();
      loadUnreviewedQueue();
    }
  } catch (err) {
    console.error('Failed to categorize:', err);
  }
}

async function dismissUnreviewed(txnId) {
  const card = document.getElementById(`reviewCard_${txnId}`);
  if (card) card.remove();

  try {
    const res = await fetch(`/api/v1/categories/${txnId}/dismiss-non-transactional`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    if (res.ok) {
      loadSummaryStats();
      loadRecentTransactions();
      loadUnreviewedQueue();
    }
  } catch (err) {
    console.error('Failed to dismiss:', err);
  }
}

async function dismissTxnDirect(txnId) {
  if (!confirm("Dismiss this item as non-transactional? An ignore rule will be learned.")) return;
  try {
    const res = await fetch(`/api/v1/categories/${txnId}/dismiss-non-transactional`, {
      method: 'POST'
    });
    if (res.ok) {
      loadSummaryStats();
      loadFullTransactions();
    }
  } catch (err) {
    console.error('Failed to dismiss txn:', err);
  }
}

async function loadCategoryCatalog() {
  try {
    const res = await fetch('/api/v1/categories/catalog');
    if (!res.ok) return;
    const list = await res.json();
    
    const filterSelect = document.getElementById('categoryFilter');
    if (filterSelect) {
      filterSelect.innerHTML = `<option value="">All Categories</option>` + list.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    }

    const budgetSelect = document.getElementById('budgetCategorySelect');
    if (budgetSelect) {
      budgetSelect.innerHTML = `<option value="">Select Category</option>` + list.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    }

    const ruleSelect = document.getElementById('ruleCategorySelect');
    if (ruleSelect) {
      ruleSelect.innerHTML = `<option value="">Map To Category</option>` + list.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    }
  } catch (err) {
    // Silently ignore catalog load error
  }
}

async function loadBudgets() {
  const container = document.getElementById('categoryBudgetsList');
  if (!container) return;

  try {
    const res = await fetch('/api/v1/budgets');
    if (!res.ok) return;
    const items = await res.json();

    if (!items || items.length === 0) {
      container.innerHTML = `<div style="color:var(--text-muted); padding:12px; text-align:center;">No custom category budgets set yet.</div>`;
      return;
    }

    container.innerHTML = items.map(b => {
      const spentFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(b.spent_inr);
      const limitFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(b.monthly_budget_inr);

      let badgeClass = 'status-active';
      let badgeText = 'Healthy';
      let barColor = 'var(--accent-success)';

      if (b.status === 'exceeded') {
        badgeClass = 'status-pending';
        badgeText = 'Exceeded';
        barColor = 'var(--accent-danger)';
      } else if (b.status === 'warning') {
        badgeClass = 'status-pending';
        badgeText = '≥80% Alert';
        barColor = 'var(--accent-warning)';
      }

      return `
        <div style="background:var(--bg-card); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:12px 14px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-weight:600; font-size:14px; color:var(--text-primary);">${escapeHtml(b.category)}</span>
              <span class="status-pill ${badgeClass}">${badgeText}</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-family:var(--font-mono); font-size:13px; color:var(--text-secondary);">${spentFormatted} / ${limitFormatted} (${b.percentage}%)</span>
              <button onclick="deleteBudget(${b.id})" class="btn-icon btn-icon-danger" title="Delete Budget">
                <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </div>
          <div class="progress-track" style="height:6px; margin-top:0;">
            <div class="progress-fill" style="width: ${Math.min(100, b.percentage)}%; background-color: ${barColor};"></div>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load budgets:', err);
  }
}

async function handleSetBudget(e) {
  e.preventDefault();
  const category = document.getElementById('budgetCategorySelect').value;
  const monthly_budget_inr = parseFloat(document.getElementById('budgetLimitInput').value);

  if (!category || !monthly_budget_inr || monthly_budget_inr <= 0) return;

  try {
    const res = await fetch('/api/v1/budgets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category, monthly_budget_inr })
    });

    if (res.ok) {
      document.getElementById('budgetLimitInput').value = '';
      loadBudgets();
      loadSummaryStats();
    }
  } catch (err) {
    console.error('Failed to save budget:', err);
  }
}

async function deleteBudget(budgetId) {
  if (!confirm('Remove this category budget limit?')) return;
  try {
    const res = await fetch(`/api/v1/budgets/${budgetId}`, { method: 'DELETE' });
    if (res.ok) {
      loadBudgets();
      loadSummaryStats();
    }
  } catch (err) {
    console.error('Failed to delete budget:', err);
  }
}

async function loadMerchantRules() {
  const container = document.getElementById('merchantRulesList');
  if (!container) return;

  try {
    let res = await fetch('/api/v1/merchant-rules');
    if (!res.ok) {
      res = await fetch('/api/v1/rules/merchant');
    }
    if (!res.ok) return;
    const rules = await res.json();

    if (!rules || rules.length === 0) {
      container.innerHTML = `<div style="color:var(--text-muted); padding:12px; text-align:center;">No merchant rules configured yet.</div>`;
      return;
    }

    container.innerHTML = rules.map(r => `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 12px; background:var(--bg-card); border:1px solid var(--border-subtle); border-radius:var(--radius-sm);">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-family:var(--font-mono); font-weight:600; font-size:13px; color:var(--text-primary);">${escapeHtml(r.merchant_pattern)}</span>
          <span style="color:var(--text-muted); font-size:12px;">→</span>
          <span class="issuer-badge">${escapeHtml(r.target_category)}</span>
        </div>
        <button onclick="deleteMerchantRule(${r.id})" class="btn-icon btn-icon-danger" title="Delete Rule">
          <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
        </button>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load merchant rules:', err);
  }
}

async function handleCreateRule(e) {
  e.preventDefault();
  const patternInput = document.getElementById('rulePatternInput');
  const categorySelect = document.getElementById('ruleCategorySelect');

  const merchant_pattern = patternInput.value.trim();
  const target_category = categorySelect.value;

  if (!merchant_pattern || !target_category) return;

  try {
    const res = await fetch('/api/v1/rules/merchant', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ merchant_pattern, target_category })
    });

    if (res.ok) {
      patternInput.value = '';
      categorySelect.value = '';
      loadMerchantRules();
      loadSummaryStats();
      loadRecentTransactions();
    }
  } catch (err) {
    console.error('Failed to create merchant rule:', err);
  }
}

async function deleteMerchantRule(ruleId) {
  if (!confirm('Delete this custom merchant rule?')) return;
  try {
    const res = await fetch(`/api/v1/rules/merchant/${ruleId}`, { method: 'DELETE' });
    if (res.ok) {
      loadMerchantRules();
    }
  } catch (err) {
    console.error('Failed to delete merchant rule:', err);
  }
}

function setupDragAndDrop() {
  const dropzone = document.getElementById('fileDropzone');
  if (!dropzone) return;

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      uploadStatementFile(files[0]);
    }
  });
}

function handleFileSelect(e) {
  const files = e.target.files;
  if (files.length > 0) {
    uploadStatementFile(files[0]);
  }
}

async function uploadStatementFile(file) {
  const statusEl = document.getElementById('uploadStatus');
  if (statusEl) {
    statusEl.style.display = 'block';
    statusEl.style.color = 'var(--text-secondary)';
    statusEl.textContent = `Uploading ${file.name}...`;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/v1/parser/upload-statement', {
      method: 'POST',
      body: formData
    });

    if (res.ok) {
      const data = await res.json();
      if (statusEl) {
        statusEl.style.color = 'var(--accent-success)';
        statusEl.textContent = `✓ Ingested ${data.ingested_count} records from ${data.filename}`;
      }
      loadSummaryStats();
      loadRecentTransactions();
    } else {
      if (statusEl) {
        statusEl.style.color = 'var(--accent-danger)';
        statusEl.textContent = `Upload failed: HTTP ${res.status}`;
      }
    }
  } catch (err) {
    if (statusEl) {
      statusEl.style.color = 'var(--accent-danger)';
      statusEl.textContent = `Upload error: ${err.message}`;
    }
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

async function loadAnalyticsTrends() {
  try {
    let res = await fetch('/api/v1/insights/monthly-trends');
    if (!res.ok) {
      res = await fetch('/api/v1/analytics/monthly-trends');
    }
    if (!res.ok) return;
    const data = await res.json();

    // KPI Banner
    const cumFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(data.cumulative_spend_inr);
    const avgFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(data.avg_monthly_spend_inr);
    const peakFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(data.peak_month_spend_inr);

    document.getElementById('valAnalyticsCumulative').textContent = cumFormatted;
    document.getElementById('valAnalyticsAvg').textContent = avgFormatted;
    document.getElementById('valAnalyticsPeak').textContent = `${data.peak_month_label} (${peakFormatted})`;

    // Insights List
    const insightsContainer = document.getElementById('analyticsInsightsList');
    if (insightsContainer && data.insights) {
      insightsContainer.innerHTML = data.insights.map(item => `<div>• ${escapeHtml(item)}</div>`).join('');
    }

    // Render Charts & Matrix
    renderMonthlyBarChart(data.monthly_totals);
    renderOverallCategoryDonut(data.overall_category_distribution);
    renderCategoryMatrix(data.monthly_matrix);

  } catch (err) {
    console.error('Failed to load analytics trends:', err);
  }
}

function renderMonthlyBarChart(monthlyTotals) {
  const container = document.getElementById('barChartContainer');
  if (!container) return;

  if (!monthlyTotals || monthlyTotals.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); align-self:center;">No monthly data available.</div>`;
    return;
  }

  const maxVal = Math.max(...monthlyTotals.map(m => m.total_spend_inr), 1);

  container.innerHTML = monthlyTotals.map(m => {
    const heightPct = Math.max(10, Math.round((m.total_spend_inr / maxVal) * 100));
    const formattedAmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(m.total_spend_inr);
    const changeBadge = m.mom_change_pct !== null 
      ? `<span style="font-size:10px; font-weight:600; color:${m.mom_change_pct >= 0 ? 'var(--accent-warning)' : 'var(--accent-success)'};">${m.mom_change_pct >= 0 ? '+' : ''}${m.mom_change_pct}%</span>`
      : '';

    return `
      <div style="display:flex; flex-direction:column; align-items:center; flex:1; max-width:80px; height:100%; justify-content:flex-end; gap:6px;">
        <div style="font-size:10px; font-family:var(--font-mono); color:var(--text-muted);">${formattedAmt}</div>
        <div style="width:100%; background:var(--accent-primary); border-radius:var(--radius-sm) var(--radius-sm) 0 0; height:${heightPct}%; min-height:8px; transition:height 0.3s ease;" title="${m.month_label}: ${formattedAmt}"></div>
        <div style="font-size:11px; font-weight:600; color:var(--text-primary); text-align:center;">${escapeHtml(m.month_label)}</div>
        ${changeBadge}
      </div>
    `;
  }).join('');
}

function renderOverallCategoryDonut(categories) {
  const container = document.getElementById('donutChartContainer');
  if (!container) return;

  if (!categories || categories.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); padding:24px; text-align:center;">No category data available.</div>`;
    return;
  }

  container.innerHTML = categories.map(cat => {
    const formatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(cat.amount_inr);
    return `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-subtle);">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="width:10px; height:10px; border-radius:50%; background-color:${cat.color_hex}; display:inline-block;"></span>
          <span style="font-size:13px; font-weight:500; color:var(--text-primary);">${escapeHtml(cat.category)}</span>
        </div>
        <div style="font-family:var(--font-mono); font-size:13px; color:var(--text-secondary);">
          ${formatted} <span style="font-size:11px; color:var(--text-muted);">(${cat.percentage}%)</span>
        </div>
      </div>
    `;
  }).join('');
}

function renderCategoryMatrix(monthlyMatrix) {
  const container = document.getElementById('analyticsMatrixContainer');
  if (!container) return;

  if (!monthlyMatrix || monthlyMatrix.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); padding:16px;">No matrix data available.</div>`;
    return;
  }

  container.innerHTML = monthlyMatrix.map(monthData => {
    return `
      <div style="background:var(--bg-app); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:14px;">
        <div style="font-weight:600; font-size:14px; color:var(--text-primary); margin-bottom:10px;">${escapeHtml(monthData.month_label)} Breakdown</div>
        <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap:10px;">
          ${monthData.categories.map(c => {
            const amtFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(c.amount_inr);
            return `
              <div style="display:flex; justify-content:space-between; align-items:center; background:var(--bg-card); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:8px 12px;">
                <span style="font-size:12px; color:var(--text-primary); text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">${escapeHtml(c.category)}</span>
                <span style="font-family:var(--font-mono); font-size:12px; font-weight:600; color:var(--text-secondary);">${amtFormatted} (${c.percentage}%)</span>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    `;
  }).join('');
}

function toggleTxnSplitControls(txnId) {
  const el = document.getElementById(`splitChips_${txnId}`);
  if (el) {
    const isHidden = el.style.display === 'none' || !el.style.display;
    el.style.display = isHidden ? 'inline-flex' : 'none';
  }
}

async function splitTransactionPreset(txnId, ratioLabel, totalInr) {
  let myShareInr = totalInr;
  if (ratioLabel === '1/2') myShareInr = round2(totalInr / 2.0);
  else if (ratioLabel === '1/3') myShareInr = round2(totalInr / 3.0);
  else if (ratioLabel === '1/4') myShareInr = round2(totalInr / 4.0);

  try {
    const res = await fetch(`/api/v1/transactions/${txnId}/split`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ my_share_inr: myShareInr, ratio_label: ratioLabel })
    });

    if (res.ok) {
      loadSummaryStats();
      loadRecentTransactions();
      loadFullTransactions();
      loadUnreviewedQueue();
    }
  } catch (err) {
    console.error('Failed to split transaction:', err);
  }
}

async function promptCustomSplit(txnId, totalInr) {
  const input = prompt(`Total bill is ₹${totalInr}. Enter YOUR personal share amount in ₹:`, Math.round(totalInr / 2));
  if (input === null) return;

  const myShareInr = parseFloat(input);
  if (isNaN(myShareInr) || myShareInr < 0 || myShareInr > totalInr) {
    alert(`Please enter a valid amount between 0 and ₹${totalInr}`);
    return;
  }

  try {
    const res = await fetch(`/api/v1/transactions/${txnId}/split`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ my_share_inr: myShareInr, ratio_label: 'custom' })
    });

    if (res.ok) {
      loadSummaryStats();
      loadRecentTransactions();
      loadFullTransactions();
      loadUnreviewedQueue();
    }
  } catch (err) {
    console.error('Failed custom split:', err);
  }
}

async function unsplitTransaction(txnId) {
  try {
    const res = await fetch(`/api/v1/transactions/${txnId}/unsplit`, {
      method: 'POST'
    });

    if (res.ok) {
      loadSummaryStats();
      loadRecentTransactions();
      loadFullTransactions();
      loadUnreviewedQueue();
    }
  } catch (err) {
    console.error('Failed to unsplit:', err);
  }
}

function round2(num) {
  return Math.round((num + Number.EPSILON) * 100) / 100;
}

// ==========================================================================
// TRIPS & TAGS CLIENT LOGIC (Impeccable Standard: Utilitarian High-Density Ledger)
// ==========================================================================

let allTagsCache = [];
let currentActiveTrip = null;
let currentPopoverTxnId = null;

async function checkActiveTripBanner() {
  try {
    const res = await fetch('/api/v1/tags/active-trip');
    if (!res.ok) return;
    const data = await res.json();
    const banner = document.getElementById('activeTripBanner');
    if (!banner) return;

    if (data.active_trip) {
      currentActiveTrip = data.active_trip;
      const iconEl = document.getElementById('activeTripIcon');
      if (iconEl) iconEl.innerHTML = getTagSvg(currentActiveTrip.icon, 18);
      
      const nameEl = document.getElementById('activeTripName');
      if (nameEl) nameEl.textContent = currentActiveTrip.name;
      
      const startStr = currentActiveTrip.start_date ? new Date(currentActiveTrip.start_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }) : '';
      const endStr = currentActiveTrip.end_date ? new Date(currentActiveTrip.end_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' }) : '';
      const totalSpendFmt = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(currentActiveTrip.total_spend_inr || 0);

      const datesEl = document.getElementById('activeTripDates');
      if (datesEl) {
        datesEl.textContent = `${startStr} – ${endStr} • ${totalSpendFmt} spent so far • Auto-tagging active`;
      }
      banner.style.display = 'flex';
    } else {
      currentActiveTrip = null;
      banner.style.display = 'none';
    }
  } catch (err) {
    console.error('Failed to check active trip:', err);
  }
}

function viewActiveTripTransactions() {
  if (!currentActiveTrip) return;
  filterByTag(currentActiveTrip.name);
}

async function populateTagFilter() {
  try {
    const res = await fetch('/api/v1/tags');
    if (!res.ok) return;
    allTagsCache = await res.json();

    const select = document.getElementById('tagFilter');
    if (!select) return;

    const currentVal = select.value;
    select.innerHTML = '<option value="">All Tags / Trips</option>' + allTagsCache.map(t => `
      <option value="${escapeHtml(t.name)}">${escapeHtml(t.name)}</option>
    `).join('');

    if (currentVal && allTagsCache.some(t => t.name === currentVal)) {
      select.value = currentVal;
    }
  } catch (err) {
    console.error('Failed to populate tag filter:', err);
  }
}

async function loadTripsAndTags() {
  const tableBody = document.getElementById('tagsTableBody');
  const mobileList = document.getElementById('tagsMobileList');
  if (!tableBody && !mobileList) return;

  try {
    const res = await fetch('/api/v1/tags');
    if (!res.ok) return;
    allTagsCache = await res.json();

    if (!allTagsCache || allTagsCache.length === 0) {
      const emptyRow = `
        <tr>
          <td colspan="7" style="text-align:center; padding:36px 16px; color:var(--text-muted);">
            <div style="font-weight:600; color:var(--text-secondary); margin-bottom:4px;">No trips or tags created yet</div>
            <div style="font-size:12px; margin-bottom:14px; max-width:400px; margin-left:auto; margin-right:auto;">
              Define an event tag with a start and end date to automatically tag incoming trip expenses.
            </div>
            <button class="btn btn-primary" onclick="toggleTripCreatorPanel(true)" style="height:32px; font-size:12px; display:inline-flex; align-items:center; gap:5px;">
              ${SVG_ICONS.plus} <span>New Trip / Tag</span>
            </button>
          </td>
        </tr>
      `;
      if (tableBody) tableBody.innerHTML = emptyRow;
      if (mobileList) mobileList.innerHTML = `<div style="text-align:center; padding:24px; color:var(--text-muted); font-size:12px;">No trips or tags defined yet</div>`;
      return;
    }

    if (tableBody) {
      tableBody.innerHTML = allTagsCache.map(tag => renderTagTableRow(tag)).join('');
    }
    if (mobileList) {
      mobileList.innerHTML = allTagsCache.map(tag => renderTagMobileCard(tag)).join('');
    }
  } catch (err) {
    console.error('Failed loading trips and tags:', err);
  }
}

function renderTagTableRow(tag) {
  const totalFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(tag.total_spend_inr || 0);

  // Date window
  let windowHtml = '<span style="font-size:12px; color:var(--text-muted);">Standard Tag</span>';
  if (tag.start_date && tag.end_date) {
    const startStr = new Date(tag.start_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
    const endStr = new Date(tag.end_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' });
    windowHtml = `
      <div style="display:inline-flex; align-items:center; gap:5px; font-size:12px; color:var(--text-secondary); font-family:var(--font-mono);">
        ${SVG_ICONS.calendar}
        <span>${startStr} – ${endStr}</span>
      </div>
    `;
  }

  // Status
  let statusHtml = '';
  if (tag.is_active_trip) {
    statusHtml = `<span class="status-pill status-cleared"><span class="pulse-dot"></span> Live Trip</span>`;
  } else if (tag.start_date && tag.end_date) {
    const now = new Date();
    const start = new Date(tag.start_date);
    const end = new Date(tag.end_date);
    if (now < start) {
      statusHtml = `<span class="status-pill status-pending">Scheduled</span>`;
    } else if (now > end) {
      statusHtml = `<span class="status-pill" style="background:rgba(100, 116, 139, 0.15); color:var(--text-muted); border:1px solid rgba(100, 116, 139, 0.3);">Concluded</span>`;
    } else {
      statusHtml = `<span class="status-pill status-cleared"><span class="pulse-dot"></span> Live Trip</span>`;
    }
  } else {
    statusHtml = `<span class="status-pill" style="background:rgba(100, 116, 139, 0.1); color:var(--text-secondary); border:1px solid var(--border-subtle);">Tag</span>`;
  }

  // Category breakdown
  let breakdownHtml = '<span style="font-size:11px; color:var(--text-muted); font-style:italic;">No expenses tagged</span>';
  if (tag.category_breakdown && tag.category_breakdown.length > 0) {
    const palette = ['#6366F1', '#10B981', '#F59E0B', '#F43F5E', '#06B6D4', '#64748B'];
    const segments = tag.category_breakdown.map((cat, idx) => {
      const col = palette[idx % palette.length];
      return `<div class="cat-dist-segment" style="width:${cat.percentage}%; background-color:${col};" title="${escapeHtml(cat.category)}: ₹${cat.amount_inr} (${cat.percentage}%)"></div>`;
    }).join('');

    const topCats = tag.category_breakdown.slice(0, 2).map((cat, idx) => {
      const col = palette[idx % palette.length];
      return `<span style="display:inline-flex; align-items:center; gap:4px; font-size:11px; color:var(--text-secondary);"><span style="width:6px; height:6px; border-radius:50%; background:${col};"></span>${escapeHtml(cat.category)} <strong style="font-family:var(--font-mono); font-weight:600; color:var(--text-primary); font-size:10px;">${cat.percentage}%</strong></span>`;
    }).join(' ');

    breakdownHtml = `
      <div style="display:flex; flex-direction:column; gap:4px;">
        <div class="cat-dist-bar">${segments}</div>
        <div style="display:flex; gap:8px; flex-wrap:wrap;">${topCats}</div>
      </div>
    `;
  }

  return `
    <tr>
      <td>
        <div style="display:flex; align-items:center; gap:8px;">
          <div style="width:28px; height:28px; border-radius:var(--radius-sm); background:rgba(99, 102, 241, 0.1); border:1px solid ${tag.color || 'var(--border-subtle)'}; display:flex; align-items:center; justify-content:center; color:${tag.color || 'var(--accent-primary)'}; flex-shrink:0;">
            ${getTagSvg(tag.icon, 14)}
          </div>
          <div>
            <div style="font-weight:600; color:var(--text-primary); font-size:13px;">${escapeHtml(tag.name)}</div>
            ${tag.description ? `<div style="font-size:11px; color:var(--text-muted);">${escapeHtml(tag.description)}</div>` : ''}
          </div>
        </div>
      </td>
      <td>${windowHtml}</td>
      <td>${statusHtml}</td>
      <td class="amount-text" style="font-family:var(--font-mono); font-weight:600;">${totalFormatted}</td>
      <td style="font-family:var(--font-mono); font-size:12px; color:var(--text-secondary);">${tag.transaction_count} txn${tag.transaction_count === 1 ? '' : 's'}</td>
      <td>${breakdownHtml}</td>
      <td style="text-align:right; white-space:nowrap;">
        <button class="btn btn-secondary btn-sm" style="height:28px; padding:0 8px; font-size:11px; margin-right:4px;" onclick="filterByTag('${escapeHtml(tag.name)}')">View in Ledger</button>
        <button class="btn btn-secondary btn-sm" style="height:28px; padding:0 8px; font-size:11px; margin-right:4px;" onclick="editTagFromButton(${tag.id})">Edit</button>
        <button class="btn-icon-only" style="width:28px; height:28px;" onclick="openDeleteTagConfirm(${tag.id}, event)" title="Delete Tag">${SVG_ICONS.trash}</button>
      </td>
    </tr>
  `;
}

function renderTagMobileCard(tag) {
  const totalFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(tag.total_spend_inr || 0);

  let dateStr = 'Standard Tag';
  if (tag.start_date && tag.end_date) {
    const startStr = new Date(tag.start_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
    const endStr = new Date(tag.end_date).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
    dateStr = `${startStr} – ${endStr}`;
  }

  let statusBadge = tag.is_active_trip 
    ? `<span class="status-pill status-cleared" style="font-size:10px; padding:1px 6px;"><span class="pulse-dot"></span> Live</span>`
    : '';

  return `
    <div class="mobile-txn-card">
      <div class="mobile-txn-top">
        <div style="display:flex; align-items:center; gap:8px;">
          <div style="width:26px; height:26px; border-radius:var(--radius-sm); background:rgba(99, 102, 241, 0.1); border:1px solid ${tag.color || 'var(--border-subtle)'}; display:flex; align-items:center; justify-content:center; color:${tag.color || 'var(--accent-primary)'};">
            ${getTagSvg(tag.icon, 13)}
          </div>
          <div>
            <div style="font-weight:600; color:var(--text-primary); font-size:13px; display:flex; align-items:center; gap:6px;">
              ${escapeHtml(tag.name)}
              ${statusBadge}
            </div>
            <div style="font-size:11px; color:var(--text-muted);">${dateStr}</div>
          </div>
        </div>
        <div class="mobile-txn-amount">${totalFormatted}</div>
      </div>
      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; border-top:1px solid var(--border-subtle); padding-top:6px;">
        <span style="font-size:11px; color:var(--text-muted); font-family:var(--font-mono);">${tag.transaction_count} txns</span>
        <div style="display:flex; gap:6px;">
          <button class="btn btn-secondary btn-sm" style="height:26px; padding:0 8px; font-size:11px;" onclick="filterByTag('${escapeHtml(tag.name)}')">View</button>
          <button class="btn btn-secondary btn-sm" style="height:26px; padding:0 8px; font-size:11px;" onclick="editTagFromButton(${tag.id})">Edit</button>
          <button class="btn-icon-only" style="width:26px; height:26px;" onclick="openDeleteTagConfirm(${tag.id}, event)" title="Delete Tag">${SVG_ICONS.trash}</button>
        </div>
      </div>
    </div>
  `;
}

function editTagFromButton(tagId) {
  const tag = allTagsCache.find(t => t.id === tagId);
  if (tag) toggleTripCreatorPanel(true, tag);
}

function filterByTag(tagName) {
  const select = document.getElementById('tagFilter');
  if (select) {
    select.value = tagName;
  }
  showSection('transactions');
  loadFullTransactions();
}

let currentEditingTagId = null;

function toggleTripCreatorPanel(forceState, tagToEdit = null) {
  const panel = document.getElementById('tripCreatorPanel');
  if (!panel) return;

  const willShow = (forceState !== undefined) ? forceState : (panel.style.display === 'none' || panel.style.display === '');

  if (willShow) {
    const titleEl = document.getElementById('tagFormTitle');
    const editIdEl = document.getElementById('tagFormEditId');
    const nameEl = document.getElementById('tagFormName');
    const descEl = document.getElementById('tagFormDescription');
    const startEl = document.getElementById('tagFormStartDate');
    const endEl = document.getElementById('tagFormEndDate');
    const autoTagEl = document.getElementById('tagFormAutoTagActive');
    const iconHidden = document.getElementById('tagFormIcon');
    const colorHidden = document.getElementById('tagFormColor');
    const submitBtn = document.getElementById('btnSaveTagSubmit');
    const deleteBtn = document.getElementById('btnDeleteTagInPanel');

    if (tagToEdit) {
      currentEditingTagId = tagToEdit.id;
      if (titleEl) titleEl.textContent = 'Edit Trip / Tag';
      if (editIdEl) editIdEl.value = tagToEdit.id;
      if (nameEl) nameEl.value = tagToEdit.name;
      if (descEl) descEl.value = tagToEdit.description || '';
      if (startEl) startEl.value = tagToEdit.start_date ? tagToEdit.start_date.split('T')[0] : '';
      if (endEl) endEl.value = tagToEdit.end_date ? tagToEdit.end_date.split('T')[0] : '';
      if (autoTagEl) autoTagEl.checked = tagToEdit.auto_tag_active !== false;
      if (iconHidden) iconHidden.value = tagToEdit.icon || 'trip';
      if (colorHidden) colorHidden.value = tagToEdit.color || '#6366F1';
      if (submitBtn) submitBtn.textContent = 'Update Trip / Tag';
      if (deleteBtn) {
        deleteBtn.style.display = 'inline-flex';
        deleteBtn.textContent = 'Delete Tag';
        deleteBtn.dataset.confirming = 'false';
      }
    } else {
      currentEditingTagId = null;
      if (titleEl) titleEl.textContent = 'Create Trip / Event Tag';
      if (editIdEl) editIdEl.value = '';
      if (nameEl) nameEl.value = '';
      if (descEl) descEl.value = '';
      if (deleteBtn) deleteBtn.style.display = 'none';

      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const returnDate = new Date();
      returnDate.setDate(returnDate.getDate() + 5);

      if (startEl) startEl.value = tomorrow.toISOString().split('T')[0];
      if (endEl) endEl.value = returnDate.toISOString().split('T')[0];
      if (autoTagEl) autoTagEl.checked = true;
      if (iconHidden) iconHidden.value = 'trip';
      if (colorHidden) colorHidden.value = '#6366F1';
      if (submitBtn) submitBtn.textContent = 'Save Tag / Trip';
    }

    const currentIcon = iconHidden ? iconHidden.value : 'trip';
    const currentColor = colorHidden ? colorHidden.value : '#6366F1';

    document.querySelectorAll('#tagIconPicker .icon-btn-choice').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-icon') === currentIcon);
    });
    document.querySelectorAll('#tagColorPicker .swatch-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-color') === currentColor);
    });

    panel.style.display = 'block';
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    if (nameEl) setTimeout(() => nameEl.focus(), 100);
  } else {
    panel.style.display = 'none';
  }
}

function selectTagIcon(btn) {
  document.querySelectorAll('#tagIconPicker .icon-btn-choice').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('tagFormIcon').value = btn.getAttribute('data-icon');
}

function selectTagColor(btn) {
  document.querySelectorAll('#tagColorPicker .swatch-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('tagFormColor').value = btn.getAttribute('data-color');
}

async function handleSaveTag(event) {
  event.preventDefault();

  const editId = document.getElementById('tagFormEditId').value;
  const name = document.getElementById('tagFormName').value.trim();
  const icon = document.getElementById('tagFormIcon').value;
  const color = document.getElementById('tagFormColor').value;
  const description = document.getElementById('tagFormDescription').value.trim();
  const startDate = document.getElementById('tagFormStartDate').value;
  const endDate = document.getElementById('tagFormEndDate').value;
  const autoTagActive = document.getElementById('tagFormAutoTagActive').checked;

  const payload = {
    name,
    icon,
    color,
    description: description || null,
    start_date: startDate ? new Date(startDate + 'T00:00:00').toISOString() : null,
    end_date: endDate ? new Date(endDate + 'T23:59:59').toISOString() : null,
    auto_tag_active: autoTagActive,
    apply_to_existing: true
  };

  try {
    let res;
    if (editId) {
      payload.reapply_date_range = true;
      res = await fetch(`/api/v1/tags/${editId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } else {
      res = await fetch('/api/v1/tags', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    }

    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || 'Failed to save tag');
      return;
    }

    toggleTripCreatorPanel(false);
    loadTripsAndTags();
    checkActiveTripBanner();
    populateTagFilter();
    loadRecentTransactions();
    loadFullTransactions();
  } catch (err) {
    console.error('Error saving tag:', err);
  }
}

function handleDeleteFromPanel() {
  if (!currentEditingTagId) return;
  openDeleteTagConfirm(currentEditingTagId);
}

function openDeleteTagConfirm(tagId, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  const tag = (allTagsCache || []).find(t => t.id === tagId);
  const tagName = tag ? tag.name : `Tag #${tagId}`;
  const txnCount = tag ? (tag.transaction_count || 0) : 0;

  const modal = document.getElementById('confirmDialog');
  const titleEl = document.getElementById('confirmDialogTitle');
  const bodyEl = document.getElementById('confirmDialogBody');
  const proceedBtn = document.getElementById('confirmDialogProceedBtn');

  if (!modal || !proceedBtn) {
    executeDeleteTag(tagId);
    return;
  }

  if (titleEl) titleEl.textContent = 'Delete Tag';
  if (bodyEl) {
    bodyEl.innerHTML = `
      Are you sure you want to permanently delete the tag <strong style="color:var(--text-primary); font-weight:600;">"${escapeHtml(tagName)}"</strong>?<br><br>
      <span style="font-size:12px; color:var(--text-muted);">
        It is currently applied to <strong style="color:var(--text-primary);">${txnCount}</strong> transaction${txnCount === 1 ? '' : 's'}. 
        All transactions will remain in your ledger, but the tag will be removed.
      </span>
    `;
  }

  proceedBtn.disabled = false;
  proceedBtn.textContent = 'Delete Tag';
  proceedBtn.onclick = () => executeDeleteTag(tagId);
  modal.style.display = 'flex';
}

function closeConfirmDialog(event) {
  if (event && event.target && event.target.id !== 'confirmDialog' && !event.target.closest('.btn-icon-only') && !event.target.closest('.btn-secondary')) {
    return;
  }
  const modal = document.getElementById('confirmDialog');
  if (modal) modal.style.display = 'none';
}

function promptDeleteTag(tagId, event) {
  openDeleteTagConfirm(tagId, event);
}

async function executeDeleteTag(tagId) {
  const proceedBtn = document.getElementById('confirmDialogProceedBtn');
  if (proceedBtn) {
    proceedBtn.disabled = true;
    proceedBtn.textContent = 'Deleting...';
  }

  try {
    const res = await fetch(`/api/v1/tags/${tagId}`, { method: 'DELETE' });
    if (res.ok) {
      const data = await res.json().catch(() => ({}));
      closeConfirmDialog();
      toggleTripCreatorPanel(false);
      showToast(`Tag "${data.tag_name || 'Tag'}" deleted successfully`, 'success');
      await loadTripsAndTags();
      await checkActiveTripBanner();
      await populateTagFilter();
      await loadRecentTransactions();
      await loadFullTransactions();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || 'Failed to delete tag', 'danger');
    }
  } catch (err) {
    console.error('Failed to delete tag:', err);
    showToast('Network error while deleting tag', 'danger');
  } finally {
    if (proceedBtn) {
      proceedBtn.disabled = false;
      proceedBtn.textContent = 'Delete Tag';
    }
  }
}

// --------------------------------------------------------------------------
// Anchored Non-Modal Dropdown Popover for Transaction Rows
// --------------------------------------------------------------------------

async function toggleTagPopover(event, txnId) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }
  const popover = document.getElementById('tagPopover');
  if (!popover) return;

  if (popover.style.display !== 'none' && currentPopoverTxnId === txnId) {
    closeTagPopover();
    return;
  }

  currentPopoverTxnId = txnId;

  // Position popover relative to button
  const triggerBtn = event.currentTarget || event.target;
  const rect = triggerBtn.getBoundingClientRect();
  
  let top = rect.bottom + window.scrollY + 6;
  let left = rect.left + window.scrollX;
  const popoverWidth = 280;

  if (left + popoverWidth > window.innerWidth - 16) {
    left = Math.max(16, window.innerWidth - popoverWidth - 16);
  }

  popover.style.top = `${top}px`;
  popover.style.left = `${left}px`;
  popover.style.display = 'flex';

  // Populate existing tags list
  const listEl = document.getElementById('popoverTagList');
  if (!allTagsCache || allTagsCache.length === 0) {
    try {
      const res = await fetch('/api/v1/tags');
      if (res.ok) allTagsCache = await res.json();
    } catch (e) {
      console.error(e);
    }
  }

  if (allTagsCache && allTagsCache.length > 0) {
    listEl.innerHTML = allTagsCache.map(tg => `
      <button type="button" class="popover-tag-item" onclick="attachTagFromPopover('${escapeHtml(tg.name)}')">
        <span style="display:inline-flex; align-items:center; color:${tg.color || '#6366F1'};">${getTagSvg(tg.icon, 12)}</span>
        <span>${escapeHtml(tg.name)}</span>
      </button>
    `).join('');
  } else {
    listEl.innerHTML = `<span style="font-size:11px; color:var(--text-muted);">No tags yet</span>`;
  }

  const input = document.getElementById('popoverTagInput');
  if (input) {
    input.value = '';
    setTimeout(() => input.focus(), 50);
  }
}

function closeTagPopover() {
  const popover = document.getElementById('tagPopover');
  if (popover) popover.style.display = 'none';
  currentPopoverTxnId = null;
}

async function attachTagFromPopover(tagName) {
  if (!currentPopoverTxnId || !tagName) return;

  try {
    const res = await fetch(`/api/v1/transactions/${currentPopoverTxnId}/tags`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag_name: tagName })
    });

    if (res.ok) {
      closeTagPopover();
      loadRecentTransactions();
      loadFullTransactions();
      loadTripsAndTags();
      checkActiveTripBanner();
    }
  } catch (err) {
    console.error('Failed to attach tag:', err);
  }
}

async function handlePopoverCreateTag(event) {
  event.preventDefault();
  const input = document.getElementById('popoverTagInput');
  if (!input) return;
  const name = input.value.trim();
  if (!name) return;

  await attachTagFromPopover(name);
}

async function removeTagFromTxn(txnId, tagIdOrName, event) {
  if (event) {
    event.stopPropagation();
    event.preventDefault();
  }

  try {
    const res = await fetch(`/api/v1/transactions/${txnId}/tags/${encodeURIComponent(tagIdOrName)}`, {
      method: 'DELETE'
    });

    if (res.ok) {
      showToast('Tag removed from transaction', 'success');
      loadRecentTransactions();
      loadFullTransactions();
      loadTripsAndTags();
      checkActiveTripBanner();
    } else {
      const err = await res.json().catch(() => ({}));
      console.error('Failed to remove tag from transaction:', err);
      showToast(err.detail || 'Failed to remove tag', 'danger');
    }
  } catch (err) {
    console.error('Failed to remove tag:', err);
    showToast('Network error while removing tag', 'danger');
  }
}

// --------------------------------------------------------------------------
// Toast Notification Utility
// --------------------------------------------------------------------------
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  let iconSvg = '';
  if (type === 'success') {
    iconSvg = `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M5 13l4 4L19 7"/></svg>`;
  } else if (type === 'danger') {
    iconSvg = `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>`;
  } else {
    iconSvg = `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;
  }

  toast.innerHTML = `
    <span style="display:inline-flex; align-items:center; flex-shrink:0;">${iconSvg}</span>
    <span>${escapeHtml(message)}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px) scale(0.95)';
    setTimeout(() => toast.remove(), 250);
  }, 3200);
}

