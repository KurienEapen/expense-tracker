package com.expensetracker.companion.ui

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.expensetracker.companion.R
import com.expensetracker.companion.data.PreferencesManager
import com.expensetracker.companion.data.model.UnreviewedTransaction
import com.expensetracker.companion.databinding.BottomSheetUnreviewedBinding
import com.google.android.material.bottomsheet.BottomSheetBehavior
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import com.google.android.material.snackbar.Snackbar
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class UnreviewedBottomSheetFragment : BottomSheetDialogFragment() {

    private var _binding: BottomSheetUnreviewedBinding? = null
    private val binding get() = _binding!!

    private lateinit var prefs: PreferencesManager
    private lateinit var adapter: UnreviewedAdapter
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    var onDismissCallback: (() -> Unit)? = null

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = BottomSheetUnreviewedBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        prefs = PreferencesManager(requireContext())

        binding.btnViewIgnoredRules.setOnClickListener {
            val fm = parentFragmentManager
            dismiss()
            IgnoredRulesBottomSheetFragment.newInstance()
                .show(fm, IgnoredRulesBottomSheetFragment.TAG)
        }

        binding.btnInspectRawSms.setOnClickListener {
            val fm = parentFragmentManager
            dismiss()
            RawMessagesBottomSheetFragment.newInstance()
                .show(fm, RawMessagesBottomSheetFragment.TAG)
        }

        setupRecyclerView()
        loadUnreviewedTransactions()
    }

    override fun onStart() {
        super.onStart()
        val dialog = dialog as? BottomSheetDialog
        dialog?.behavior?.apply {
            state = BottomSheetBehavior.STATE_EXPANDED
            skipCollapsed = true
        }
    }

    private fun setupRecyclerView() {
        adapter = UnreviewedAdapter(
            items = mutableListOf(),
            onCategorize = { txn, category, position ->
                categorizeTransaction(txn, category, position)
            },
            onMoreOptions = { txn, position ->
                showMoreCategoriesDialog(txn, position)
            },
            onDismissNonTransactional = { txn, position ->
                dismissNonTransactional(txn, position)
            }
        )
        binding.rvUnreviewed.layoutManager = LinearLayoutManager(requireContext())
        binding.rvUnreviewed.adapter = adapter
    }

    private fun loadUnreviewedTransactions() {
        val serverUrl = prefs.serverUrl.trim().trimEnd('/')
        binding.progressLoading.visibility = View.VISIBLE
        binding.layoutEmptyState.visibility = View.GONE
        binding.rvUnreviewed.visibility = View.GONE

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val request = Request.Builder()
                    .url("$serverUrl/api/v1/categories/unreviewed?limit=50")
                    .get()
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    if (response.isSuccessful && body != null) {
                        val type = object : TypeToken<List<UnreviewedTransaction>>() {}.type
                        val list: List<UnreviewedTransaction> = Gson().fromJson(body, type)

                        withContext(Dispatchers.Main) {
                            binding.progressLoading.visibility = View.GONE
                            if (list.isEmpty()) {
                                binding.layoutEmptyState.visibility = View.VISIBLE
                                binding.rvUnreviewed.visibility = View.GONE
                            } else {
                                binding.layoutEmptyState.visibility = View.GONE
                                binding.rvUnreviewed.visibility = View.VISIBLE
                                adapter.updateList(list)
                            }
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            binding.progressLoading.visibility = View.GONE
                            showSnackbar("Failed to load review items: HTTP ${response.code}")
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressLoading.visibility = View.GONE
                    showSnackbar("Network error: ${e.message}")
                }
            }
        }
    }

    private fun categorizeTransaction(txn: UnreviewedTransaction, category: String, position: Int) {
        val serverUrl = prefs.serverUrl.trim().trimEnd('/')
        
        // Optimistically remove from adapter for snappy UX
        adapter.removeItemAt(position)
        if (adapter.isEmpty()) {
            binding.layoutEmptyState.visibility = View.VISIBLE
            binding.rvUnreviewed.visibility = View.GONE
        }

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val jsonPayload = JsonObject().apply {
                    addProperty("category", category)
                }
                val reqBody = jsonPayload.toString().toRequestBody("application/json; charset=utf-8".toMediaType())

                val request = Request.Builder()
                    .url("$serverUrl/api/v1/categories/${txn.id}/categorize")
                    .post(reqBody)
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    if (response.isSuccessful) {
                        Log.i(TAG, "Categorized txn #${txn.id} as '$category'")
                    } else {
                        Log.w(TAG, "Server rejected categorization: HTTP ${response.code}")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to submit category: ${e.message}")
            }
        }
    }

    private fun dismissNonTransactional(txn: UnreviewedTransaction, position: Int) {
        val serverUrl = prefs.serverUrl.trim().trimEnd('/')

        // Optimistically remove from adapter
        adapter.removeItemAt(position)
        if (adapter.isEmpty()) {
            binding.layoutEmptyState.visibility = View.VISIBLE
            binding.rvUnreviewed.visibility = View.GONE
        }

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val emptyBody = "{}".toRequestBody("application/json; charset=utf-8".toMediaType())
                val request = Request.Builder()
                    .url("$serverUrl/api/v1/categories/${txn.id}/dismiss-non-transactional")
                    .post(emptyBody)
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    if (response.isSuccessful && body != null) {
                        val json = Gson().fromJson(body, JsonObject::class.java)
                        val ruleObj = json.getAsJsonObject("rule")
                        val ruleId = ruleObj?.get("id")?.asInt
                        val cascaded = json.get("cascaded_count")?.asInt ?: 0

                        withContext(Dispatchers.Main) {
                            val msg = if (cascaded > 0) {
                                "Ignored ($cascaded matching also auto-dismissed)"
                            } else {
                                "Ignored • Learned rule for future messages"
                            }
                            val snack = Snackbar.make(binding.root, msg, Snackbar.LENGTH_LONG)
                            if (ruleId != null) {
                                snack.setAction("UNDO") {
                                    undoIgnoreRule(ruleId)
                                }
                            }
                            snack.show()
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            showSnackbar("Server rejected dismissal: HTTP ${response.code}")
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    showSnackbar("Network error: ${e.message}")
                }
            }
        }
    }

    private fun undoIgnoreRule(ruleId: Int) {
        val serverUrl = prefs.serverUrl.trim().trimEnd('/')
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val request = Request.Builder()
                    .url("$serverUrl/api/v1/categories/ignore-rules/$ruleId")
                    .delete()
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    withContext(Dispatchers.Main) {
                        if (response.isSuccessful) {
                            showSnackbar("Ignore rule undone.")
                            loadUnreviewedTransactions()
                        }
                    }
                }
            } catch (e: Exception) {
                // Ignore network error on undo
            }
        }
    }

    private fun showMoreCategoriesDialog(txn: UnreviewedTransaction, position: Int) {
        val extraCategories = arrayOf("Utilities", "Entertainment", "Health", "Investment", "Transfer", "Other")
        MaterialAlertDialogBuilder(requireContext())
            .setTitle("Choose Category")
            .setItems(extraCategories) { dialog, which ->
                val selected = extraCategories[which]
                categorizeTransaction(txn, selected, position)
                dialog.dismiss()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showSnackbar(message: String) {
        view?.let {
            Snackbar.make(it, message, Snackbar.LENGTH_SHORT).show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
        onDismissCallback?.invoke()
    }

    companion object {
        const val TAG = "UnreviewedBottomSheet"
        fun newInstance() = UnreviewedBottomSheetFragment()
    }
}
