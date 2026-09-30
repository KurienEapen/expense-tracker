package com.expensetracker.companion.ui

import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.expensetracker.companion.data.PreferencesManager
import com.expensetracker.companion.data.model.IgnoredRule
import com.expensetracker.companion.databinding.BottomSheetIgnoredRulesBinding
import com.google.android.material.bottomsheet.BottomSheetBehavior
import com.google.android.material.bottomsheet.BottomSheetDialog
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import com.google.android.material.snackbar.Snackbar
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

class IgnoredRulesBottomSheetFragment : BottomSheetDialogFragment() {

    private var _binding: BottomSheetIgnoredRulesBinding? = null
    private val binding get() = _binding!!

    private lateinit var prefs: PreferencesManager
    private lateinit var adapter: IgnoredRulesAdapter
    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = BottomSheetIgnoredRulesBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        prefs = PreferencesManager(requireContext())

        setupRecyclerView()
        loadIgnoredRules()
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
        adapter = IgnoredRulesAdapter(
            items = mutableListOf(),
            onDeleteRule = { rule, position ->
                deleteRule(rule, position)
            }
        )
        binding.rvIgnoredRules.layoutManager = LinearLayoutManager(requireContext())
        binding.rvIgnoredRules.adapter = adapter
    }

    private fun loadIgnoredRules() {
        val serverUrl = prefs.serverUrl.trim().trimEnd('/')
        binding.progressLoading.visibility = View.VISIBLE
        binding.layoutEmptyState.visibility = View.GONE
        binding.rvIgnoredRules.visibility = View.GONE

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val request = Request.Builder()
                    .url("$serverUrl/api/v1/categories/ignore-rules")
                    .get()
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    val body = response.body?.string()
                    if (response.isSuccessful && body != null) {
                        val type = object : TypeToken<List<IgnoredRule>>() {}.type
                        val list: List<IgnoredRule> = Gson().fromJson(body, type)

                        withContext(Dispatchers.Main) {
                            binding.progressLoading.visibility = View.GONE
                            if (list.isEmpty()) {
                                binding.layoutEmptyState.visibility = View.VISIBLE
                                binding.rvIgnoredRules.visibility = View.GONE
                            } else {
                                binding.layoutEmptyState.visibility = View.GONE
                                binding.rvIgnoredRules.visibility = View.VISIBLE
                                adapter.updateList(list)
                            }
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            binding.progressLoading.visibility = View.GONE
                            showSnackbar("Failed to load rules: HTTP ${response.code}")
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

    private fun deleteRule(rule: IgnoredRule, position: Int) {
        val serverUrl = prefs.serverUrl.trim().trimEnd('/')

        adapter.removeItemAt(position)
        if (adapter.isEmpty()) {
            binding.layoutEmptyState.visibility = View.VISIBLE
            binding.rvIgnoredRules.visibility = View.GONE
        }

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val request = Request.Builder()
                    .url("$serverUrl/api/v1/categories/ignore-rules/${rule.id}")
                    .delete()
                    .build()

                httpClient.newCall(request).execute().use { response ->
                    withContext(Dispatchers.Main) {
                        if (response.isSuccessful) {
                            showSnackbar("Rule deleted. Future messages matching this will be parsed.")
                        } else {
                            showSnackbar("Failed to delete rule on server.")
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    showSnackbar("Failed to delete rule: ${e.message}")
                }
            }
        }
    }

    private fun showSnackbar(message: String) {
        view?.let {
            Snackbar.make(it, message, Snackbar.LENGTH_SHORT).show()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    companion object {
        const val TAG = "IgnoredRulesSheet"
        fun newInstance() = IgnoredRulesBottomSheetFragment()
    }
}
