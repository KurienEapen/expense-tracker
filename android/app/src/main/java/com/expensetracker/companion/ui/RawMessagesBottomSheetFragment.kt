package com.expensetracker.companion.ui

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.expensetracker.companion.R
import com.expensetracker.companion.data.PreferencesManager
import com.expensetracker.companion.data.model.RawMessageItem
import com.expensetracker.companion.databinding.BottomSheetRawMessagesBinding
import com.expensetracker.companion.databinding.DialogConvertRawBinding
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
import java.util.regex.Pattern

class RawMessagesBottomSheetFragment : BottomSheetDialogFragment() {

    private var _binding: BottomSheetRawMessagesBinding? = null
    private val binding get() = _binding!!

    private lateinit var prefs: PreferencesManager
    private lateinit var adapter: RawMessagesAdapter
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    var onConvertedCallback: (() -> Unit)? = null

    private var filterUnparsedOnly = true

    private val categories = arrayOf(
        "Food & Dining",
        "Shopping & E-Commerce",
        "Groceries & Essentials",
        "Travel & Commute",
        "Fuel",
        "Bills & Utilities",
        "Entertainment & Subscriptions",
        "Health & Medical",
        "Transfers",
        "Other"
    )

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = BottomSheetRawMessagesBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        prefs = PreferencesManager(requireContext())

        setupRecyclerView()
        setupFilters()
        loadRawMessages()
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
        adapter = RawMessagesAdapter(
            items = mutableListOf(),
            onConvert = { item, position ->
                showConvertDialog(item, position)
            }
        )
        binding.rvRawMessages.layoutManager = LinearLayoutManager(requireContext())
        binding.rvRawMessages.adapter = adapter
    }

    private fun setupFilters() {
        binding.chipGroupFilter.setOnCheckedStateChangeListener { _, checkedIds ->
            filterUnparsedOnly = checkedIds.contains(R.id.chipUnparsedOnly)
            loadRawMessages()
        }
    }

    private fun loadRawMessages() {
        val serverUrl = prefs.serverUrl.trim().trimEnd('/')
        binding.progressLoading.visibility = View.VISIBLE
        binding.layoutEmptyState.visibility = View.GONE
        binding.rvRawMessages.visibility = View.GONE

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val url = "$serverUrl/api/v1/ingest/raw-messages?unparsed_only=$filterUnparsedOnly&limit=50"
                val request = Request.Builder()
                    .url(url)
                    .get()
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    if (response.isSuccessful && body != null) {
                        val type = object : TypeToken<List<RawMessageItem>>() {}.type
                        val list: List<RawMessageItem> = Gson().fromJson(body, type)

                        withContext(Dispatchers.Main) {
                            binding.progressLoading.visibility = View.GONE
                            if (list.isEmpty()) {
                                binding.layoutEmptyState.visibility = View.VISIBLE
                                binding.rvRawMessages.visibility = View.GONE
                                if (filterUnparsedOnly) {
                                    binding.tvEmptyTitle.text = "No unparsed messages"
                                    binding.tvEmptySubtitle.text = "All captured SMS have been recognized as transactions or matched by ignore rules."
                                } else {
                                    binding.tvEmptyTitle.text = "No SMS found"
                                    binding.tvEmptySubtitle.text = "No SMS messages have been captured or synced from this phone yet."
                                }
                            } else {
                                binding.layoutEmptyState.visibility = View.GONE
                                binding.rvRawMessages.visibility = View.VISIBLE
                                adapter.updateList(list)
                            }
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            binding.progressLoading.visibility = View.GONE
                            showSnackbar("Failed to load SMS list: HTTP ${response.code}")
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

    private fun showConvertDialog(item: RawMessageItem, position: Int) {
        val dialogBinding = DialogConvertRawBinding.inflate(layoutInflater)
        dialogBinding.tvRawSnippet.text = item.body

        // Auto-extract amount guess from SMS text
        val amountPattern = Pattern.compile("(?i)(?:(?:rs\\.?|inr)\\s*([\\d,]+(?:\\.\\d{1,2})?)|spent\\s*(?:rs\\.?|inr)?\\s*([\\d,]+(?:\\.\\d{1,2})?))")
        val matcher = amountPattern.matcher(item.body)
        if (matcher.find()) {
            val rawAmt = (matcher.group(1) ?: matcher.group(2))?.replace(",", "")
            if (!rawAmt.isNullOrBlank()) {
                dialogBinding.etAmount.setText(rawAmt)
            }
        }

        // Auto-populate Category dropdown
        val catAdapter = ArrayAdapter(requireContext(), android.R.layout.simple_dropdown_item_1line, categories)
        dialogBinding.actvCategory.setAdapter(catAdapter)
        dialogBinding.actvCategory.setText(categories[0], false)

        val dialog = MaterialAlertDialogBuilder(requireContext())
            .setTitle("Convert to Transaction")
            .setView(dialogBinding.root)
            .setPositiveButton("Convert & Save Rule", null) // Set null to handle validation in onShowListener
            .setNegativeButton("Cancel", null)
            .create()

        dialog.setOnShowListener {
            val positiveBtn = dialog.getButton(android.content.DialogInterface.BUTTON_POSITIVE)
            positiveBtn.setOnClickListener {
                val merchant = dialogBinding.etMerchant.text?.toString()?.trim() ?: ""
                val amountStr = dialogBinding.etAmount.text?.toString()?.trim() ?: ""
                val category = dialogBinding.actvCategory.text?.toString()?.trim() ?: categories[0]
                val amountVal = amountStr.toDoubleOrNull()

                if (merchant.isBlank()) {
                    dialogBinding.etMerchant.error = "Merchant name is required"
                    return@setOnClickListener
                }
                if (amountVal == null || amountVal <= 0) {
                    dialogBinding.etAmount.error = "Valid amount is required"
                    return@setOnClickListener
                }

                dialog.dismiss()
                submitConversion(item, position, merchant, amountVal, category)
            }
        }

        dialog.show()
    }

    private fun submitConversion(
        item: RawMessageItem,
        position: Int,
        merchant: String,
        amount: Double,
        category: String
    ) {
        val serverUrl = prefs.serverUrl.trim().trimEnd('/')
        binding.progressLoading.visibility = View.VISIBLE

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val payload = JsonObject().apply {
                    addProperty("amount_inr", amount)
                    addProperty("merchant", merchant)
                    addProperty("category", category)
                    addProperty("transaction_type", "debit")
                }
                val reqBody = payload.toString().toRequestBody("application/json; charset=utf-8".toMediaType())

                val request = Request.Builder()
                    .url("$serverUrl/api/v1/ingest/convert-raw/${item.id}")
                    .post(reqBody)
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    withContext(Dispatchers.Main) {
                        binding.progressLoading.visibility = View.GONE
                        if (response.isSuccessful && body != null) {
                            val respJson = Gson().fromJson(body, JsonObject::class.java)
                            val txnId = respJson.get("parsed_transaction_id")?.asInt
                            adapter.updateItemConverted(position, txnId)

                            val msg = "Classified as '$category' • Learned rule for '$merchant'"
                            showSnackbar(msg)
                            onConvertedCallback?.invoke()
                        } else {
                            showSnackbar("Server rejected conversion: HTTP ${response.code}")
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

    private fun showSnackbar(message: String) {
        view?.let {
            Snackbar.make(it, message, Snackbar.LENGTH_LONG).show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    companion object {
        const val TAG = "RawMessagesBottomSheet"
        fun newInstance() = RawMessagesBottomSheetFragment()
    }
}
