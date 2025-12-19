FROM node:20.17.0

RUN mkdir -p /usr/src/app/next

WORKDIR /usr/src/app/next

COPY package*.json ./

RUN npm install

COPY . .

RUN npm run build

RUN ls

EXPOSE 3000

CMD [ "npm", "run", "start" ]
