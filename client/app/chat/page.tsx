import LeagalAreaSection from "@/components/chat/legal-area-selector"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Plus, SendHorizonal } from "lucide-react"

export default function ChatPage() {
  return (
    <div className="flex h-dvh w-full flex-col items-center justify-center">
      <div className="flex flex-1 flex-col items-center justify-center">
        <h1 className="font-heading text-2xl font-bold">
          Welcome to legalease
        </h1>
        <p className="text-muted-foreground">
          Ask any legal question and get instant answers.
        </p>
      </div>
      <div className="mb-4 flex items-center justify-center gap-2">
        <div className="flex items-center justify-center gap-2">
          <LeagalAreaSection />
          <Tooltip>
            <TooltipTrigger asChild>
              <Button size={"icon"} variant={"outline"}>
                <Plus />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Add documents to analyze</p>
            </TooltipContent>
          </Tooltip>

          <Textarea
            placeholder="Type your question here..."
            className="min-h-auto w-full min-w-3xl"
          />
          <Button size={"lg"}>
            <SendHorizonal /> Send
          </Button>
        </div>
      </div>
    </div>
  )
}
