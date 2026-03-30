"use client"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export default function LeagalAreaSection() {
  return (
    <Select>
      <SelectTrigger className="w-45">
        <SelectValue placeholder="Select Legal Area" />
      </SelectTrigger>
      <SelectContent position="popper" align="center">
        <SelectGroup>
          <SelectItem value="consumer">Consumer Protection</SelectItem>
          <SelectItem value="labour">Labour & Employment</SelectItem>
          <SelectItem value="family">Family Law</SelectItem>
        </SelectGroup>
      </SelectContent>
    </Select>
  )
}
