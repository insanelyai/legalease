"use client"

import { useForm, useWatch } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"

import LeagalAreaSection from "@/components/chat/legal-area-selector"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

import { Field, FieldGroup, FieldSet, FieldLabel } from "@/components/ui/field"

import { Plus, SendHorizonal } from "lucide-react"
import { LEGAL_AREA } from "@/types"
import { Input } from "@/components/ui/input"
import { toast } from "sonner"
import { useEffect } from "react"

const schema = z.object({
  message: z.string().min(10, "Ask something meaningful"),

  legalArea: z.enum(["CP", "LE", "FW"], {
    message: "Select a legal area",
  }),

  file: z
    .any()
    .optional()
    .refine((file) => !file || file instanceof File, "Invalid file"),
})

export default function ChatPage() {
  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
  })

  const onSubmit = (data: z.infer<typeof schema>) => {
    console.log(data)

    // 🔥 IMPORTANT: file handling
    const formData = new FormData()
    formData.append("message", data.message)
    formData.append("legalArea", data.legalArea)

    if (data.file) {
      formData.append("file", data.file)
    }

    // send to API
  }

  const selectedFile = useWatch({
    control,
    name: "file",
  })

  useEffect(() => {
    if (errors) {
      if (errors.message) {
        toast.error(errors.message.message)
      }

      if (errors.legalArea) {
        toast.error(errors.legalArea.message)
      }
    }
    if (selectedFile) {
      toast.success(`Selected file: ${selectedFile.name}`)
    }
  }, [errors, selectedFile])

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

      {/* <form
        onSubmit={handleSubmit(onSubmit)}
        className="mb-4 flex w-full items-center justify-center gap-2"
      >
        <FieldSet className="mx-auto flex w-full items-center justify-center">
          <FieldGroup className="flex w-full flex-row items-center justify-center gap-2">
            <LeagalAreaSection />

            <Tooltip>
              <TooltipTrigger asChild>
                <Button type="button" size="icon" variant="outline">
                  <Plus />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Add documents to analyze</p>
              </TooltipContent>
            </Tooltip>

            <Field className="w-125">
              <FieldLabel htmlFor="message" className="sr-only">
                Message
              </FieldLabel>

              <Textarea
                id="message"
                placeholder="Type your question here..."
                className="min-h-10 resize-none"
                {...register("message")}
              />

              {errors.message && (
                <FieldDescription className="text-red-500">
                  {errors.message.message}
                </FieldDescription>
              )}
            </Field>

            <Button type="submit" size="lg" disabled={isSubmitting}>
              <SendHorizonal className="mr-1 h-4 w-4" />
              Send
            </Button>
          </FieldGroup>
        </FieldSet>
      </form> */}

      <form
        onSubmit={handleSubmit(onSubmit)}
        className="mb-4 flex w-full items-center justify-center gap-2"
      >
        <FieldSet className="mx-auto flex w-full items-center justify-center">
          <FieldGroup className="flex w-full flex-row items-center justify-center gap-2">
            {/* 🔹 Legal Area Select */}
            <Field className="w-45">
              <FieldLabel className="sr-only">Legal Area</FieldLabel>

              <LeagalAreaSection
                onValueChange={(value: LEGAL_AREA) =>
                  setValue("legalArea", value)
                }
              />
            </Field>

            {/* 🔹 File Upload inside Tooltip */}
            <Popover>
              <PopoverTrigger asChild>
                <Button type="button" size="icon" variant="outline">
                  <Plus />
                </Button>
              </PopoverTrigger>

              <PopoverContent
                className="w-64 space-y-2"
                align="center"
                sideOffset={10}
              >
                <Field>
                  <FieldLabel>Upload document</FieldLabel>

                  <Input
                    type="file"
                    onChange={(e) => {
                      const file = e.target.files?.[0]
                      setValue("file", file)
                    }}
                  />
                </Field>
              </PopoverContent>
            </Popover>

            {/* 🔹 Message */}
            <Field className="w-125">
              <FieldLabel htmlFor="message" className="sr-only">
                Message
              </FieldLabel>

              <Textarea
                id="message"
                placeholder="Type your question here..."
                className="min-h-10 resize-none"
                {...register("message")}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit(onSubmit)()
                  }
                }}
              />
            </Field>

            {/* 🔹 Submit */}
            <Button type="submit" size="lg" disabled={isSubmitting}>
              <SendHorizonal className="mr-1 h-4 w-4" />
              Send
            </Button>
          </FieldGroup>
        </FieldSet>
      </form>
    </div>
  )
}
