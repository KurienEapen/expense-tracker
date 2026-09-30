package com.expensetracker.companion.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.expensetracker.companion.data.model.IgnoredRule
import com.expensetracker.companion.databinding.ItemIgnoredRuleBinding

class IgnoredRulesAdapter(
    private var items: MutableList<IgnoredRule>,
    private val onDeleteRule: (rule: IgnoredRule, position: Int) -> Unit
) : RecyclerView.Adapter<IgnoredRulesAdapter.ViewHolder>() {

    class ViewHolder(val binding: ItemIgnoredRuleBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemIgnoredRuleBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return ViewHolder(binding)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]
        val binding = holder.binding

        binding.tvRuleDescription.text = item.displayTitle
        binding.tvRuleMeta.text = item.displayMeta
        binding.tvRuleSampleText.text = item.sampleText ?: "No preview snippet available"

        binding.btnDeleteRule.setOnClickListener {
            onDeleteRule(item, holder.adapterPosition)
        }
    }

    fun removeItemAt(position: Int) {
        if (position in 0 until items.size) {
            items.removeAt(position)
            notifyItemRemoved(position)
            notifyItemRangeChanged(position, items.size - position)
        }
    }

    fun updateList(newItems: List<IgnoredRule>) {
        items = newItems.toMutableList()
        notifyDataSetChanged()
    }

    fun isEmpty(): Boolean = items.isEmpty()
}
