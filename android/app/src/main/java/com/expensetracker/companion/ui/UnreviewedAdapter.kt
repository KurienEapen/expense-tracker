package com.expensetracker.companion.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.expensetracker.companion.data.model.UnreviewedTransaction
import com.expensetracker.companion.databinding.ItemUnreviewedTransactionBinding
import java.util.Locale

class UnreviewedAdapter(
    private var items: MutableList<UnreviewedTransaction>,
    private val onCategorize: (transaction: UnreviewedTransaction, category: String, position: Int) -> Unit,
    private val onMoreOptions: (transaction: UnreviewedTransaction, position: Int) -> Unit
) : RecyclerView.Adapter<UnreviewedAdapter.ViewHolder>() {

    class ViewHolder(val binding: ItemUnreviewedTransactionBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemUnreviewedTransactionBinding.inflate(
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

        binding.tvMerchant.text = item.displayMerchant
        binding.tvAmount.text = String.format(Locale.getDefault(), "₹%.2f", item.amountInr)
        binding.tvMeta.text = item.displayMeta

        // Reset click listeners on chips
        binding.chipDining.setOnClickListener {
            onCategorize(item, "Dining", holder.adapterPosition)
        }
        binding.chipGroceries.setOnClickListener {
            onCategorize(item, "Groceries", holder.adapterPosition)
        }
        binding.chipShopping.setOnClickListener {
            onCategorize(item, "Shopping", holder.adapterPosition)
        }
        binding.chipTravel.setOnClickListener {
            onCategorize(item, "Travel", holder.adapterPosition)
        }
        binding.chipFuel.setOnClickListener {
            onCategorize(item, "Fuel", holder.adapterPosition)
        }
        binding.chipMore.setOnClickListener {
            onMoreOptions(item, holder.adapterPosition)
        }
    }

    fun removeItemAt(position: Int) {
        if (position in 0 until items.size) {
            items.removeAt(position)
            notifyItemRemoved(position)
            notifyItemRangeChanged(position, items.size - position)
        }
    }

    fun updateList(newItems: List<UnreviewedTransaction>) {
        items = newItems.toMutableList()
        notifyDataSetChanged()
    }

    fun isEmpty(): Boolean = items.isEmpty()
}
