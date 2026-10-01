package com.expensetracker.companion.ui

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
import com.expensetracker.companion.R
import com.expensetracker.companion.data.model.RawMessageItem
import com.expensetracker.companion.databinding.ItemRawMessageBinding

class RawMessagesAdapter(
    private var items: MutableList<RawMessageItem>,
    private val onConvert: (RawMessageItem, Int) -> Unit
) : RecyclerView.Adapter<RawMessagesAdapter.ViewHolder>() {

    class ViewHolder(val binding: ItemRawMessageBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val binding = ItemRawMessageBinding.inflate(
            LayoutInflater.from(parent.context),
            parent,
            false
        )
        return ViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]
        val context = holder.itemView.context

        holder.binding.tvRawSender.text = item.sender
        holder.binding.tvRawDate.text = item.displayDate
        holder.binding.tvRawBody.text = item.body

        if (item.isParsed) {
            holder.binding.tvRawStatusBadge.text = if (item.transactionId != null) "✓ Parsed #${item.transactionId}" else "✓ Parsed"
            holder.binding.tvRawStatusBadge.setBackgroundResource(R.drawable.badge_pill_healthy)
            holder.binding.tvRawStatusBadge.setTextColor(ContextCompat.getColor(context, R.color.status_healthy))
            holder.binding.btnConvertToTxn.text = "Re-classify"
        } else {
            holder.binding.tvRawStatusBadge.text = "Ignored / Unparsed"
            holder.binding.tvRawStatusBadge.setBackgroundResource(R.drawable.badge_pill_warning)
            holder.binding.tvRawStatusBadge.setTextColor(ContextCompat.getColor(context, R.color.status_warning))
            holder.binding.btnConvertToTxn.text = "✨ Convert to Transaction"
        }

        holder.binding.btnConvertToTxn.setOnClickListener {
            val pos = holder.adapterPosition
            if (pos != RecyclerView.NO_POSITION) {
                onConvert(item, pos)
            }
        }
    }

    override fun getItemCount(): Int = items.size

    fun updateList(newItems: List<RawMessageItem>) {
        items.clear()
        items.addAll(newItems)
        notifyDataSetChanged()
    }

    fun updateItemConverted(position: Int, transactionId: Int?) {
        if (position in items.indices) {
            items[position].isParsed = true
            items[position].transactionId = transactionId
            notifyItemChanged(position)
        }
    }

    fun isEmpty(): Boolean = items.isEmpty()
}
