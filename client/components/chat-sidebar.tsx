import React from "react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "./ui/sidebar"
import {  Scale, SquarePen } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar"

export default function AppSidebar() {
  const chats = [
    {
      id: "1",
      title: "Contract Review – NDA",
      lastMessage: "Can you check clause 4?",
      updatedAt: "2026-03-28T10:30:00Z",
    },
    {
      id: "2",
      title: "Startup Legal Setup",
      lastMessage: "Need help with incorporation",
      updatedAt: "2026-03-28T09:15:00Z",
    },
    {
      id: "3",
      title: "Employment Agreement",
      lastMessage: "Is this clause enforceable?",
      updatedAt: "2026-03-27T18:45:00Z",
    },
    {
      id: "4",
      title: "IP Rights Discussion",
      lastMessage: "Who owns the code?",
      updatedAt: "2026-03-27T14:20:00Z",
    },
    {
      id: "5",
      title: "Freelancer Contract",
      lastMessage: "Payment terms look off",
      updatedAt: "2026-03-26T20:10:00Z",
    },
    {
      id: "6",
      title: "Privacy Policy Draft",
      lastMessage: "Add GDPR section?",
      updatedAt: "2026-03-26T16:00:00Z",
    },
    {
      id: "7",
      title: "Terms of Service",
      lastMessage: "Need a simpler version",
      updatedAt: "2026-03-25T22:30:00Z",
    },
    {
      id: "8",
      title: "Investor Agreement",
      lastMessage: "Equity split looks wrong",
      updatedAt: "2026-03-25T19:05:00Z",
    },
  ]

  return (
    <Sidebar>
      {/* 🔹 HEADER */}
      <SidebarHeader>
        <div className="flex items-center justify-start gap-2 p-2">
          <div>
            <Scale size={24} strokeWidth={1.5} className="text-primary" />
          </div>
          {/* <div>
            <h1 className="font-heading text-lg tracking-tight">legalease</h1>
          </div> */}
        </div>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton>
              <SquarePen />
              New Chat
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      {/* 🔹 CHAT LIST */}
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Your chats</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {chats.map((chat) => {
                return (
                  <SidebarMenuItem key={chat.id}>
                    <SidebarMenuButton>
                      <p>
                        <span className="font-medium">{chat.title}</span>
                      </p>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton className="h-auto flex items-center justify-start gap-2">
              <Avatar>
                <AvatarImage src="https://github.com/shadcn.png" />
                <AvatarFallback>CN</AvatarFallback>
              </Avatar>
              <div className="flex flex-col">
                <span className="font-heading">insanelyai</span>
                <span className="text-xs">hasansayyed.personal@gmail.com</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
