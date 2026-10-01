// AdultMoney Web PWA Dashboard Logic

document.addEventListener('DOMContentLoaded', () => {
  initAppTitle();
  loadCategoryCatalog();
  loadSummaryStats();
  loadRecentTransactions();
  loadUnreviewedQueue();
  setupDragAndDrop();

  handleHashRouting();
  window.addEventListener('hashchange', handleHashRouting);
});

function handleHashRouting() {
  const rawHash = (window.location.hash || '#dashboard').replace('#', '').trim();
  const validSections = ['dashboard', 'transactions', 'review', 'budgets', 'analytics', 'upload'];
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
  const sections = ['sectionDashboard', 'sectionTransactions', 'sectionReview', 'sectionBudgets', 'sectionAnalytics'];
  const titleMap = {
    'dashboard': 'Dashboard',
    'transactions': 'All Transactions',
    'analytics': 'Monthly Analytics & Category Trends',
    'budgets': 'Budgets & Custom Rules',
    'review': '1-Tap Ambiguity Review Queue',
    'upload': 'Statement Import'
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
  if (!items || items.length === 0) {
    container.innerHTML = `<div style="color:var(--text-muted); padding:12px;">No card data available.</div>`;
    return;
  }

  container.innerHTML = items.map(iss => {
    const formatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(iss.amount_inr);
    return `
      <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-subtle);">
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="issuer-badge">${escapeHtml(iss.issuer)}</span>
          <span style="font-size:12px; color:var(--text-muted);">${iss.count} txn${iss.count > 1 ? 's' : ''}</span>
        </div>
        <span style="font-family:var(--font-mono); font-weight:600; color:var(--text-primary);">${formatted}</span>
      </div>
    `;
  }).join('');
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

  let url = `/api/v1/transactions?limit=100`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (category) url += `&category=${encodeURIComponent(category)}`;

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
    ? `<div style="font-size:11px; color:var(--text-secondary); margin-top:2px; display:flex; align-items:center; gap:4px;"><span style="color:var(--accent-warning);">📍</span> ${escapeHtml(t.location_name)}</div>`
    : '';

  const nonSplittable = ['Transfers & Payments', 'Transfer', 'Rewards & Cashback'];
  const isCredit = t.transaction_type === 'credit';
  const isEligibleCategory = !nonSplittable.includes(categoryStr);
  const isSplittable = !isCredit && isEligibleCategory && (t.amount_inr > 0);

  let splitBadgeHtml = '';
  if (t.is_split) {
    const myShareFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.my_share_inr);
    const recFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.reimbursable_inr);
    splitBadgeHtml = `
      <div style="font-size:11px; color:var(--accent-primary); margin-top:3px; display:inline-flex; align-items:center; gap:6px; background:rgba(59, 130, 246, 0.08); padding:2px 8px; border-radius:4px; border:1px solid rgba(59, 130, 246, 0.18);">
        <span>✂️ Split (${t.split_ratio_label}): My Share ${myShareFormatted} • Owed ${recFormatted}</span>
        <button onclick="unsplitTransaction(${t.id})" style="background:none; border:none; color:var(--accent-danger); cursor:pointer; font-size:11px; font-weight:600; padding:0 2px;" title="Cancel Split">✕</button>
      </div>
    `;
  } else if (isSplittable) {
    splitBadgeHtml = `
      <div style="display:inline-flex; align-items:center; gap:3px; margin-top:3px;">
        <span style="font-size:10px; font-weight:600; color:var(--text-muted); letter-spacing:0.03em;">SPLIT:</span>
        <button onclick="splitTransactionPreset(${t.id}, '1/2', ${t.amount_inr})" class="btn-icon" style="height:18px; padding:0 5px; font-size:10px; border-radius:3px;" title="Split 50/50">½</button>
        <button onclick="splitTransactionPreset(${t.id}, '1/3', ${t.amount_inr})" class="btn-icon" style="height:18px; padding:0 5px; font-size:10px; border-radius:3px;" title="Split 1/3">⅓</button>
        <button onclick="promptCustomSplit(${t.id}, ${t.amount_inr})" class="btn-icon" style="height:18px; padding:0 5px; font-size:10px; border-radius:3px;" title="Custom Share">✎</button>
      </div>
    `;
  }


  return `
    <tr>
      <td class="merchant-cell">
        ${escapeHtml(merchant)}
        ${locationBadgeHtml}
        ${splitBadgeHtml}
      </td>
      <td><span class="chip" style="min-height:26px; padding:2px 8px; font-size:11px; margin:0; display:inline-flex; align-items:center;">${escapeHtml(categoryStr)}</span></td>
      <td><span class="issuer-badge">${escapeHtml(issuerStr)}</span></td>
      <td style="font-size:12px; color:var(--text-muted);">${dateFormatted}</td>
      <td class="amount-text">${totalAmountFormatted}</td>
      ${showAction ? `<td><button class="btn-icon-only" style="width:32px; height:32px;" onclick="dismissTxnDirect(${t.id})" title="Dismiss as Non-Expense"><svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button></td>` : ''}
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
    ? `<div style="font-size:11px; color:var(--text-secondary); margin-top:2px;"><span style="color:var(--accent-warning);">📍</span> ${escapeHtml(t.location_name)}</div>`
    : '';

  const nonSplittable = ['Transfers & Payments', 'Transfer', 'Rewards & Cashback'];
  const isCredit = t.transaction_type === 'credit';
  const isEligibleCategory = !nonSplittable.includes(categoryStr);
  const isSplittable = !isCredit && isEligibleCategory && (t.amount_inr > 0);

  let splitControlsHtml = '';
  if (t.is_split) {
    const myShareFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.my_share_inr);
    const recFormatted = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(t.reimbursable_inr);
    splitControlsHtml = `
      <div style="font-size:11px; color:var(--accent-primary); margin-top:6px; display:flex; justify-content:space-between; align-items:center; background:rgba(59, 130, 246, 0.08); padding:4px 8px; border-radius:var(--radius-sm); border:1px solid rgba(59, 130, 246, 0.18);">
        <span>✂️ Split: My Share ${myShareFormatted} | Owed ${recFormatted}</span>
        <button onclick="unsplitTransaction(${t.id})" style="background:none; border:none; color:var(--accent-danger); cursor:pointer; font-size:11px; font-weight:600;">✕ Unsplit</button>
      </div>
    `;
  } else if (isSplittable) {
    splitControlsHtml = `
      <div style="display:flex; align-items:center; gap:6px; margin-top:6px;">
        <span style="font-size:11px; color:var(--text-muted);">Split:</span>
        <button onclick="splitTransactionPreset(${t.id}, '1/2', ${t.amount_inr})" class="chip" style="min-height:22px; padding:2px 8px; font-size:10px;">½ Split</button>
        <button onclick="splitTransactionPreset(${t.id}, '1/3', ${t.amount_inr})" class="chip" style="min-height:22px; padding:2px 8px; font-size:10px;">⅓ Split</button>
        <button onclick="promptCustomSplit(${t.id}, ${t.amount_inr})" class="chip" style="min-height:22px; padding:2px 8px; font-size:10px;">Custom Share</button>
      </div>
    `;
  }


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
        </div>
        <span>${dateFormatted}</span>
      </div>
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
        splitNotice = `<div style="font-size:11px; color:var(--accent-primary); font-weight:600; margin-top:4px;">✂️ Split Active: My Share ₹${t.my_share_inr} | Owed ₹${t.reimbursable_inr}</div>`;
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
              <button class="chip" onclick="categorizeUnreviewed(${t.id}, 'Dining')">🍔 Dining</button>
              <button class="chip" onclick="categorizeUnreviewed(${t.id}, 'Groceries')">🛒 Groceries</button>
              <button class="chip" onclick="categorizeUnreviewed(${t.id}, 'Shopping')">🛍️ Shopping</button>
              <button class="chip" onclick="categorizeUnreviewed(${t.id}, 'Travel')">✈️ Travel</button>
              <button class="chip" onclick="categorizeUnreviewed(${t.id}, 'Fuel')">⛽ Fuel</button>
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
