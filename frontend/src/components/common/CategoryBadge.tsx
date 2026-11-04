import React from "react";
import { ProductCategory } from "@/types";

interface CategoryBadgeProps {
  category: ProductCategory | string;
}

const CATEGORY_MAP: Record<string, { label: string; style: string }> = {
  food_grocery: {
    label: "Food & Grocery",
    style: "bg-blue-50 text-blue-700 border-blue-200",
  },
  beverage: {
    label: "Beverages",
    style: "bg-teal-50 text-teal-700 border-teal-200",
  },
  personal_care: {
    label: "Personal Care",
    style: "bg-purple-50 text-purple-700 border-purple-200",
  },
  household: {
    label: "Household",
    style: "bg-indigo-50 text-indigo-700 border-indigo-200",
  },
};

export default function CategoryBadge({ category }: CategoryBadgeProps) {
  const config = CATEGORY_MAP[category] || {
    label: category,
    style: "bg-gray-100 text-gray-700 border-gray-200",
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${config.style}`}
    >
      {config.label}
    </span>
  );
}
