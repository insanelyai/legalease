"use client"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { LEGAL_AREA } from "@/types"

export default function LeagalAreaSection({
  onValueChange,
}: {
  onValueChange: (value: LEGAL_AREA) => void
}) {
  return (
    <Select onValueChange={onValueChange}>
      <SelectTrigger className="w-45">
        <SelectValue placeholder="Select Legal Area" />
      </SelectTrigger>
      <SelectContent position="popper" align="center">
        <SelectGroup>
          <SelectItem value="CP">Consumer Protection</SelectItem>
          <SelectItem value="LE">Labour & Employment</SelectItem>
          <SelectItem value="FW">Family Law</SelectItem>
        </SelectGroup>
      </SelectContent>
    </Select>
  )
}
